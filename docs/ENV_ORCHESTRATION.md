 # Orquestração por ambiente e pipelines CI/CD

Este documento descreve, com nível operacional, como orquestrar e implantar os contêineres do projeto em quatro ambientes: Desenvolvimento, Homologação, Pré-produção e Produção. Inclui também os pipelines de CI/CD (GitHub Actions) adequados para cada ambiente, comandos, nomes de secrets e recomendações de segurança e rollback.

Obs: tudo abaixo assume que o projeto contém o código Python (app/`school_schedule.py`), `Dockerfile`, os manifests Kubernetes em `k8s/` e workflows em `.github/workflows/`.

---

## Visão geral de ambientes

- desenvolvimento (dev)
  - Uso: desenvolvimento iterativo, testes manuais, GUI via Docker Compose e/ou Docker Desktop.
  - Orquestrador: Docker Compose para rápido feedback; Kubernetes local (Docker Desktop ou kind) para testes de integração.
  - Branch associado: `develop` ou `dev` (opcional).

- homologação (homolog)
  - Uso: validação por QA com dados mais próximos da produção.
  - Orquestrador: Kubernetes (cluster de homolog).
  - Branch associado: `release/*` ou `homolog`.

- pré-produção (preprod)
  - Uso: validação final, testes de carga e smoke tests.
  - Orquestrador: Kubernetes (cluster de pré-produção configurado com recursos próximos à produção).
  - Branch associado: `main` ou `preprod` (ou build a partir de tag).

- produção (prod)
  - Uso: tráfego real.
  - Orquestrador: Kubernetes (prod), com políticas de deploy controladas (revisões, approvals).
  - Branch associado: `main`/`master` e tags `v*` para releases.

---

## Estratégia de imagens e tags

- Tagging:
  - dev: `:dev-${{ github.run_id }}` ou `:latest-dev`
  - homolog: `:homolog-${{ github.run_id }}`
  - preprod: `:preprod-${{ github.run_id }}`
  - prod: `:vX.Y.Z` (via tag de release)
- Registro recomendado: GitHub Container Registry (`ghcr.io`) ou Docker Hub. Use secrets para credenciais.
- Nome do repositório de imagem: `ghcr.io/<org>/school_scheduler` ou `<dockerhub_user>/school_scheduler`.

---

## Configuração de Kubernetes (conceitos e arquivos)

- Namespaces por ambiente: `school-scheduler-dev`, `school-scheduler-homolog`, `school-scheduler-preprod`, `school-scheduler-prod`.
- Manifests recomendados (em `k8s/`):
  - `namespace-<env>.yaml` (ou usar kustomize overlays)
  - `secret-<env>-example.yaml` (apenas modelo; criar secrets com `kubectl create secret`)
  - `mysql-statefulset.yaml` (PVCs via `volumeClaimTemplates`)
  - `mysql-headless-svc.yaml` (headless service para StatefulSet)
  - `app-deployment.yaml` (use Kustomize ou Helm para parametrizar `image`, `replicas`, `resources`)
  - `app-service.yaml` (ClusterIP ou LoadBalancer para prod)
  - `ingress.yaml` (Ingress/ingressRoute com TLS para prod)

- Recomendação: usar Kustomize overlays ou Helm chart para parametrizar diferenças (replicas, resources, image tag, probes, ingress, config).

---

## Secrets e configuração sensível

- Nunca comitar credenciais em texto claro. Use:
  - `kubectl create secret generic db-credentials --from-literal=user=root --from-literal=rootpassword=XXX -n <ns>`
  - Em CI: armazenar `DB_PASSWORD`, `DOCKERHUB_TOKEN`, `GITHUB_TOKEN` (se necessário), `KUBECONFIG` (base64) e outras credenciais.
- Nomes de secrets esperados pelo repositório:
  - `DB_PASSWORD` (root password) — CI tests
  - `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` — optional
  - `KUBECONFIG` — base64-encoded kubeconfig para deploy automático (opcional)
  - `GITHUB_TOKEN` — GH Actions built-in (use para GHCR)

---

## CI/CD: pipeline por ambiente (padrão GitHub Actions)

Princípio: cada ambiente tem um pipeline específico com responsabilidades claras.

1) Pipeline de Desenvolvimento (workflow `ci-cd.yml` atual — executa em push/PR)
  - Gatilho: push para `develop` e PRs.
  - Jobs:
    - lint (ruff)
    - build + unit tests (matrix Python opcional)
    - build image (opcional) e publicar em GHCR/DockerHub com tag `dev-<run-id>`
    - (opcional) deploy para `school-scheduler-dev` em cluster dev (ex.: Docker Desktop)
  - Secrets necessários: `DB_PASSWORD`, opcional `DOCKERHUB_*`.

2) Pipeline de Homologação (workflow `ci-homolog.yml`)
  - Gatilho: push para branch `release/*` ou PR merge para `homolog`.
  - Jobs:
    - Executar testes de integração (conectar-se a um banco de dados de homologação gerenciado ou provisório)
    - Build e push de imagem para registry com tag `homolog-<run-id>`
    - Deploy para `school-scheduler-homolog` (kubectl apply / helm upgrade)
    - Rodar smoke tests (endpoints mínimos, verificações de DB)
  - Secrets necessários: `KUBECONFIG_HOMOLOG` (ou service account), `DB_PASSWORD_HOMOLOG`, `REGISTRY creds`.

3) Pipeline Pré-produção (workflow `ci-preprod.yml`)
  - Gatilho: merge para `main` ou push com tag `preprod/*`.
  - Jobs:
    - Re-executar todos os testes (unit + integração)
    - Build & push image `preprod-<run-id>` ou `sha-<commit>`
    - Deploy para `school-scheduler-preprod` com `helm upgrade --install` ou kubectl (use canary/blue-green strategy if supported)
    - Run e2e tests and load tests (if configured)
    - Manual approval gate before promoting to prod (optional)
  - Secrets: `KUBECONFIG_PREPROD`, `REGISTRY creds`.

4) Pipeline Produção (workflow `ci-prod.yml`)
  - Gatilho: tag de release `v*` ou merge para `main` seguido de manual approval.
  - Jobs:
    - Build image and push with immutable tag `vX.Y.Z` (from git tag)
    - Run pre-deploy checks (security scans, image signature if used)
    - Manual approval (GitHub environment protection)
    - Deploy to `school-scheduler-prod` using `helm upgrade --install` ou kubectl apply
    - Post-deploy rollout checks: `kubectl rollout status`, health check endpoints, smoke tests
    - Monitor for errors for a window (e.g., 10 minutes) and auto-rollback if failures detected
  - Secrets: `KUBECONFIG_PROD`, `REGISTRY creds`, other secrets from secret manager.

---

## Estrutura de um job de deploy (exemplo)

1) Build & push image (GHCR)

```yaml
- name: Build and push GHCR image
  uses: docker/build-push-action@v4
  with:
    context: .
    push: true
    tags: ghcr.io/<org>/school_scheduler:${{ github.ref_name || github.sha }}
```

2) Apply manifests and wait rollout

```yaml
- name: Deploy to cluster
  run: |
    echo "$KUBECONFIG" | base64 --decode > kubeconfig
    export KUBECONFIG=$(pwd)/kubeconfig
    # update image in deployment (if templated) or run helm upgrade
    kubectl set image deployment/school-scheduler school-scheduler=ghcr.io/<org>/school_scheduler:${{ github.ref_name || github.sha }} -n school-scheduler-prod
    kubectl rollout status deployment/school-scheduler -n school-scheduler-prod --timeout=120s
```

3) Smoke test and verification

```yaml
- name: Smoke test
  run: |
    # curl health endpoint (adjust endpoint)
    curl -f https://app.prod.example.com/health || (kubectl rollout undo deployment/school-scheduler -n school-scheduler-prod; exit 1)
```

---

## Rollback and promotion

- Rollback strategies:
  - `kubectl rollout undo deployment/<name> -n <ns>`
  - Helm: `helm rollback <release> <revision>`
  - Automated rollback in pipeline if smoke tests fail
- Promotion:
  - Promote image by tag: if preprod tests pass, trigger prod pipeline that pulls the same image tag (immutable)
  - Use GitHub Releases/tags to mark releases and trigger prod workflow

---

## Backups, monitoring e observabilidade

- MySQL backups: configure backup job (cronjob) que faz `mysqldump` e armazena em storage seguro (S3, GCS)
- Monitoring: Prometheus + Grafana para métricas; configure alerts para pod restarts, error rates, DB health
- Logging: centralizar logs (ELK/EFK, Loki) para facilitar diagnóstico de CrashLoopBackOff/erros de runtime

---

## Comandos úteis (recap)

- Docker Compose (dev):
```powershell
docker compose -f .\docker-compose.dev.yml -f .\docker-compose.gui.yml up --build
```
- Build image local (Docker Desktop):
```powershell
docker build -t school_scheduler-app:latest .
```
- Apply k8s manifests (dev cluster):
```powershell
kubectl apply -f k8s/namespace-dev.yaml
kubectl apply -f k8s/secret-example.yaml
kubectl apply -f k8s/mysql-statefulset.yaml
kubectl apply -f k8s/app-deployment-dev.yaml
kubectl apply -f k8s/app-service-dev.yaml
```
- Rollout status:
```powershell
kubectl rollout status deployment/school-scheduler -n school-scheduler-dev
```

---

## Segurança e boas práticas

- Use least-privilege para service accounts e tokens (Kubernetes RBAC)
- Não exponha a porta 3306 do MySQL para a Internet; use redes privadas ou port-forward para debug
- Automate secret provisioning com um secret manager (Vault, SealedSecrets, SOPS)
- Configure branch protection e approvals para `main/master` + environment protections in GitHub (required reviewers for prod deploy)

---

## Próximos passos sugeridos (priorizados)

1. Converter os manifests para Helm Chart ou Kustomize overlays — facilita promoção entre ambientes.
2. Adicionar `Job` para geração headless dentro de k8s e criar um workflow de agendamento (cron).
3. Criar workflows separados em `.github/workflows/` para `homolog`, `preprod` e `prod` com gates (approvals) e testes pós-deploy.
4. Integrar backup da base MySQL (CronJob) e política de retenção.

---

Se quiser, eu crio: Helm chart básico + 3 workflows prontos (homolog/preprod/prod) com gates e exemplos de secrets. Quer que eu gere esses artefatos agora?
