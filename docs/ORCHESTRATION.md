Orquestração e CI/CD para ProjetoDevops
=====================================

Resumo
------
Este documento descreve uma proposta de orquestração por ambientes (desenvolvimento, homologação, pré-produção e produção) e pipelines de CI/CD separados para cada ambiente usando GitHub Actions. As opções ilustradas usam Docker Compose para ambientes locais/desenvolvimento e Kubernetes para homologação/pré-produção/produção, com imagens armazenadas em um registry (Docker Hub, GitHub Container Registry ou outro privado).

Visão geral dos ambientes
- desenvolvimento: execução local usando `docker-compose.dev.yml`. Ciclo rápido, monta códigos por volume e expõe portas para debug.
- homologação: ambiente para validação manual/QA; pode ser kubernetes namespace `homolog` ou um cluster menor; deploy automatizado via pipeline `ci-homolog.yml`.
- pré-produção: ambiente de integração final próximo à produção (namespace `preprod`), deploy por pipeline `ci-preprod.yml`.
- produção: ambiente `prod` com alta disponibilidade e políticas de deploy controladas; pipeline `ci-prod.yml` com gates e aprovações manuais.

Princípios
- Branching:
  - `main` -> produção
  - `preprod` -> pré-produção
  - `homolog` -> homologação
  - `dev` -> desenvolvimento (pull requests integradas aqui)
- Cada push ou PR em cada branch dispara o pipeline específico ao ambiente.
- Imagens são versionadas com `sha` e `tag` (ex: `projetodevops:sha-<short>` e `projetodevops:latest` em dev).

Requisitos
- Acesso a um registry (Docker Hub, GHCR). Credenciais armazenadas como segredos no repositório (ex.: DOCKER_USERNAME, DOCKER_PASSWORD ou GHCR_TOKEN).
- Um cluster Kubernetes para homolog/preprod/prod com `kubectl` configurado no pipeline (usando KUBECONFIG ou credenciais do provedor).
- GitHub Actions com segredos configurados: DOCKERHUB_USERNAME, DOCKERHUB_TOKEN, KUBE_CONFIG_HOM, KUBE_CONFIG_PREPROD, KUBE_CONFIG_PROD, etc.

Arquitetura dos serviços
- service: `school-scheduler` (aplicação Python). Dependências: MySQL (pod/serviço) e opcionalmente Redis.
- DB: MySQL executado como serviço separado (em compose) ou provisionado no cluster.

Conteúdo deste repositório
- `docker-compose.dev.yml` — orquestração local, monta código via volume.
- `docker-compose.homolog.yml` — exemplo para reproduzir homolog localmente (sem volumes, com imagens publicadas).
- `k8s/` — manifests de Deployment/Service/ConfigMap/Secret/Ingress (templates).
- `.github/workflows/ci-dev.yml`, `ci-homolog.yml`, `ci-preprod.yml`, `ci-prod.yml` — pipelines exemplares.

Procedimento resumido para deploy local (desenvolvimento)
1. Ajuste `.env` com variáveis (DB_HOST, DB_USER...) ou use variáveis de ambiente no terminal.
2. Execute:
   docker compose -f docker-compose.dev.yml up --build

Procedimento resumido para deploy em k8s (homolog/preprod/prod)
1. Build e push da imagem para o registry (feito pelo pipeline): `docker build -t <registry>/projetodevops:<tag> .` e `docker push ...`.
2. Atualizar `k8s/deployment.yaml` com a nova image tag (o pipeline faz isso automaticamente via `kubectl set image` ou kustomize/helm).
3. Aplicar: `kubectl apply -f k8s/ -n <env>`

Rollback
- Em pipelines Kubernetes, usar `kubectl rollout undo deployment/<name> -n <env>` para voltar para a versão anterior.

Segurança
- Nunca commit credenciais em texto plano. Use GitHub Secrets, Vault ou parâmetros do provedor de nuvem.

Detalhamento e exemplos de arquivos estão presentes nos templates abaixo neste repositório.
