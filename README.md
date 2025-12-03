
# Projeto: School Scheduler — trabalho académico

Este repositório contém o trabalho que desenvolvi para a disciplina: um sistema de agendamento escolar escrito em Python. O objetivo foi implementar um protótipo funcional que permita cadastrar professores, turmas e disciplinas, e gerar um cronograma otimizado usando programação linear (PuLP). A interface principal usa Tkinter e os dados são persistidos em MySQL.

Este documento resume a implementação, explica como executar localmente (incluindo a GUI no Windows), descreve a pipeline de CI/CD que configurei com GitHub Actions, e traz notas sobre execução com Docker Compose e deploy em Kubernetes.

Sumário rápido
- Linguagem: Python 3.x
- Banco: MySQL (containerizado em Docker para testes/execução)
- Otimização: PuLP (programação linear)
- GUI: Tkinter (apresentada via X forwarding quando em container)
- Testes: unittest
- CI/CD: GitHub Actions (workflows por ambiente)

Estrutura principal do repositório
- `school_schedule.py` — aplicação principal (lógica, DB, GUI e otimização).
- `tests/test_schedule.py` — casos de teste que valem pela integração básica com o DB e pela execução do gerador de cronograma.
- `requirements.txt` — dependências do projeto.
- `Dockerfile` — imagem base para empacotar a aplicação.
- `docker-compose.*.yml` — perfis para rodar dev/homolog/preprod/prod/gui/local.
- `.github/workflows/*.yml` — workflows de CI/CD por ambiente.

Como executar (visão do autor)

1) Ambiente Python local (desenvolvimento rápido):

```powershell
pip install -r requirements.txt
pip install mysql-connector-python pulp
python school_schedule.py
```

Observação: `school_schedule.py` abre uma interface Tkinter se executado diretamente. Para executar apenas funções de backend (por exemplo nas rotinas de teste), garanta que o arquivo permita execução sem abrir a GUI (veja a seção "Tornar import-safe").

2) Executando os testes localmente:

```powershell
python -m unittest tests.test_schedule -v
```

Docker e Docker Compose (minha abordagem)

Para isolar e padronizar ambientes, criei vários arquivos `docker-compose`:

- `docker-compose.dev.yml` — desenvolvimento local com build da imagem e mapeamento de portas.
- `docker-compose.homolog.yml` — perfil de homologação; pode apontar para imagem do registry ou ser ajustado para `build:` local.
- `docker-compose.preprod.yml` / `docker-compose.prod.yml` — perfis para testar a mesma imagem em portas distintas.
- `docker-compose.gui.yml` — para executar a GUI em container; no Windows uso `DISPLAY=host.docker.internal:0.0` e um X server (VcXsrv).
- `docker-compose.local.yml` — compose utilitário para testes automatizados com MySQL temporário.

Comandos úteis (PowerShell):

```powershell
# Subir ambiente de desenvolvimento
docker compose -f docker-compose.dev.yml up --build

# Subir GUI local (execute o X Server antes — VcXsrv / XLaunch)
docker compose -f docker-compose.gui.yml up --build
```

Detalhes dos workflows de CI (por ambiente)

A seguir descrevo, no meu próprio formato de trabalho académico, o que cada workflow faz e por que o configurei assim.

- `ci-dev.yml` — objetivo: validação rápida em ambiente de desenvolvimento.
	- Quando é executado: push em branches de desenvolvimento e `workflow_dispatch` para execuções manuais.
	- Principais passos: checkout do código, configuração do Python, instalação de dependências, iniciar um MySQL temporário (via `docker run`) apenas quando os segredos necessários estão disponíveis, executar os testes unitários com debug extra (discovery explícito) e gerar artefatos de build locais.
	- Uso: indicado para validar mudanças de código antes de enviar para homologação.

- `ci-homolog.yml` — objetivo: validar a imagem que será homologada.
	- Quando é executado: push em branches de homologação e `workflow_dispatch`.
	- Principais passos: além dos passos do `ci-dev`, este workflow pode construir a imagem Docker e, se houver segredos de registry, fazer login e push para um registry privado ou GHCR (passos protegidos por condicionais).
	- Observação: em repositórios forkados os segredos não estão disponíveis — por isso os passos de push são pulados automaticamente.

- `ci-preprod.yml` — objetivo: integração mais próxima da produção.
	- Comportamento: constrói a imagem com as mesmas configurações que a produção e roda um conjunto de testes/integrations smoke tests; prepara artefatos que podem ser promovidos ao ambiente de produção.

- `ci-prod.yml` — objetivo: pipeline de release/produção.
	- Segurança: o job de deploy para produção está configurado com `environment: production` para suportar approvals/revisões no GitHub (proteções do Environment).
	- Operações sensíveis (push de imagens e deploy) só ocorrem se os segredos de registry e `KUBECONFIG_BASE64` estiverem presentes.

- `ci-cd.yml` — pipeline central / referência.
	- Função: reúne as etapas principais de build/test/deploy e é usado como modelo. Contém a lógica de build com Buildx, normalização de tags (owner/repo em minúsculas) e passos de deploy opcionais.

Como os workflows tratam secrets e o MySQL

- Para evitar erros de validação do YAML (quando se usa `secrets.*` em expressões de parsing), exportei os `secrets` para variáveis `env` no nível do job e usei `env.*` nas condicionais dos passos.
- Quando preciso iniciar o MySQL com credenciais sensíveis, eu executo `docker run` dentro do job e aguardo a disponibilidade do serviço — essa abordagem permite passar senhas que não ficam visíveis no arquivo do workflow.
- Os passos de login/push ao registry são condicionais: só rodarão se `env.DOCKERHUB_USERNAME` / `env.REGISTRY` estiverem definidos.

Arquivos Kubernetes (pasta `k8s/`) — descrição dos manifestos

O repositório contém uma pasta `k8s/` com manifests que usei para testar deploys em cluster. Abaixo descrevo cada arquivo e por que ele existe:

- `k8s/namespace-dev.yaml` — define o namespace `dev` para isolar recursos de desenvolvimento.
- `k8s/secret-example.yaml` — exemplo de secret (NÃO aplicar em produção sem adaptar). Serve como modelo para criar secrets com `kubectl create secret`.
- `k8s/mysql-deployment.yaml` — deployment (ou manifest) que cria uma instância de MySQL para ambientes que não precisem de persistência complexa.
- `k8s/mysql-statefulset.yaml` — StatefulSet para MySQL quando é necessário armazenamento persistente com identidade de pod.
- `k8s/mysql-headless-svc.yaml` — serviço headless para descoberta de pods do MySQL (usado com StatefulSet).
- `k8s/app-deployment-dev.yaml` — Deployment do aplicativo (imagem, variáveis de ambiente, probes) para ambiente de desenvolvimento.
- `k8s/app-service-dev.yaml` — Service que expõe o `app-deployment-dev` internamente no cluster.
- `k8s/deployment.yaml` e `k8s/service.yaml` — manifests mais genéricos que podem ser usados como base para deploys em outros ambientes (pré-produção/produção) — normalmente preciso ajustar `replicas`, `resources` e `image` antes de aplicar.
- `k8s/README.md` — notas e instruções rápidas contidas na pasta (recomendo revisar antes de aplicar).

Recomendações práticas sobre os manifests

- Não aplique `secret-example.yaml` sem substituir valores por secrets reais via `kubectl create secret generic` ou via CI com GitHub Secrets.
- Para testes locais, use `imagePullPolicy: IfNotPresent` ou ajuste as imagens para apontar a tags locais geradas pelo workflow.
- Ordem sugerida de aplicação para testes locais: namespace → secrets → storage (PVCs/statefulset) → banco (MySQL) → app (deployment/service).

CI/CD — o que implementei

Desenvolvi workflows específicos por ambiente: `ci-dev.yml`, `ci-homolog.yml`, `ci-preprod.yml` e `ci-prod.yml`, além de um pipeline central `ci-cd.yml`. Principais pontos técnicos:

- Trigger/manual: adicionei `workflow_dispatch` para permitir disparos manuais durante a validação. Os workflows também reagem a push/PR conforme o fluxo normal.
- MySQL no runner: para usar segredos com segurança, o MySQL é iniciado dinamicamente dentro do job via `docker run` (em vez de usar `services:`). O job espera o banco ficar pronto antes de executar os testes.
- Secrets: para evitar validações inválidas do YAML, exporto `secrets.*` em variáveis `env` no nível do job e uso `env.*` nas condicionais dos passos.
- Build e push: uso Buildx para construir imagens e somente executo login/push quando os segredos de registry (Docker Hub/GHCR) estão presentes — isso evita falhas em forks/PRs.
- Tagging: normalizo o owner/repo para minúsculas ao gerar tags para evitar erros em registries que exigem nomes lowercase.

Notas sobre Kubernetes

Com os manifests (pasta `k8s/` ou `manifests/`), os workflows estão preparados para receber um `KUBECONFIG_BASE64` como secret e executar o deploy. Recomendações que segui:

- Proteja o `kubeconfig` como Secret no repositório e limite permissões.
- Use `environment: production` nas jobs de deploy para aproveitar approvals do GitHub Environments.
- Revise cuidadosamente os manifests e os Secrets injetados pelo workflow antes de aplicar no cluster.

GUI no Windows (nota prática)

Para abrir a interface Tkinter a partir do container no Windows eu uso VcXsrv (XLaunch):

1. Instale e execute VcXsrv (Multiple windows). Permita conexões.
2. Garanta que `host.docker.internal` resolva e que o firewall permita conexões locais.
3. Suba o compose GUI:

```powershell
docker compose -f docker-compose.gui.yml up --build
```

Se usar WSL2 pode ser necessário substituir `host.docker.internal` pelo IP do host.

Tornar o código import-safe (recomendação do autor)

Para facilitar execução de testes em CI, é recomendável garantir que `school_schedule.py` não abra a GUI automaticamente ao ser importado. Idealmente:

- Encapsular a inicialização da GUI em `if __name__ == '__main__':`.
- Expor funções e classes utilitárias (conexão DB, criação de tabelas, geração de cronograma) para que os testes possam chamar sem instanciar a interface.

Troubleshooting rápido

- "No tests ran": execute `python -m unittest discover -v tests` localmente; verifique nomes de arquivos e se o diretório `tests/` está no repositório.
- Erro ao push para GHCR: confirme que owner/repo está em minúsculas e que o token tem permissão `packages:write`.
- MySQL não fica pronto no CI: consulte `docker logs <mysql-container>` ou aumente o timeout/wait loop no workflow.
- GUI: erro "no display name and no $DISPLAY environment variable": rode o X Server e use o `docker-compose.gui.yml` com `DISPLAY` apontando para o host.

Detalhes práticos sobre os workflows
- Triggers e workflows por ambiente:
	- `ci-dev.yml`, `ci-homolog.yml`, `ci-preprod.yml`, `ci-prod.yml`: workflows com `workflow_dispatch` para execução manual e gatilhos em push/PR. Cada workflow contém passos para instalar dependências, executar os testes e opcionalmente realizar build/push da imagem para um registry quando as credenciais estiverem presentes.
	- `ci-cd.yml`: pipeline principal (build + testes + etapas de deploy/integração), usada como referência central.
	- Push para registries (GHCR ou Docker Hub) é guardado atrás de checagens: as etapas de login/push só rodam se as variáveis de ambiente/segredos necessários estiverem definidos (útil para forks/PRs onde secrets não estão disponíveis).

- Observações sobre imagem e tagging:
	- O nome do owner/repositório usado para taggar a imagem é normalizado para minúsculas no momento do build para evitar erros de tag com letras maiúsculas em registries como GHCR.


Existem vários perfis de execução via Docker Compose para facilitar desenvolvimento, homologação, preprod e produção locais:

- `docker-compose.homolog.yml` — perfil homologação. Pode referenciar uma imagem remota (registry) ou ser ajustado para `build:` localmente para testes.
- `docker-compose.preprod.yml` e `docker-compose.prod.yml` — perfis para testar a imagem em ambientes que simulam a produção; por padrão expõem portas diferentes para rodar vários ambientes em paralelo.
- `docker-compose.gui.yml` — configuração para executar a aplicação com interface gráfica (Tkinter) em containers. No Windows, a compose define `DISPLAY: host.docker.internal:0.0` para encaminhar a exibição para um servidor X (VcXsrv / XLaunch).
- `docker-compose.local.yml` — utilitário para testes locais que pode trazer um MySQL temporário e um serviço que executa os testes automaticamente.
Exemplos de uso (PowerShell, Windows):

```powershell
# Rodar ambiente de desenvolvimento
docker compose -f docker-compose.dev.yml up --build

# Rodar GUI local (antes, execute o X Server — p.ex. VcXsrv / XLaunch)
docker compose -f docker-compose.gui.yml up --build
```

## Testes

Para executar os testes localmente use:

```powershell
python -m unittest tests.test_schedule -v
```

No CI, os workflows executam os testes com um banco MySQL temporário iniciado durante o job. Se os testes não encontrarem nenhum caso, os workflows incluem passos de debug que listam arquivos e executam a descoberta explícita (`python -m unittest discover -v tests` e fallback para execução direta do módulo de teste).

## Build e push de imagem Docker (CI)

Os workflows usam o Buildx para criar imagens e fazem push para registries quando as credenciais estão disponíveis. Principais pontos:

- Antes de push, o workflow executa um passo de login para o registry (GHCR/Docker Hub) usando segredos definidos no repositório.
- Os steps de push são protegidos por checagens `if: env.REGISTRY` / `if: env.DOCKERHUB_USERNAME` para evitar tentativas de push em forks ou runs sem segredos.

Se você quiser testar build localmente:

```powershell
docker build -t school-scheduler:local .
```

## Kubernetes (k8s)

Se este repositório contiver manifests de Kubernetes (por exemplo uma pasta `k8s/` ou `manifests/`), os workflows podem usar um `kubeconfig` (codificado em base64 guardado como secret) para aplicar recursos no cluster. Notas importantes:

- Proteja o `kubeconfig` como um GitHub Secret com permissão mínima necessária.
- O job de deploy para produção foi configurado para usar `environment: production` — isso permite integrar a proteção de ambiente do GitHub (revisores/approvals) antes de executar o deploy.
- Antes de aplicar manifests no cluster, revise os arquivos de deployment e os Secrets gerados pelo workflow para evitar vazamento de credenciais.

## Secrets e configuração do GitHub

Para permitir que os workflows façam build/push e inicializem serviços protegidos, configure os seguintes Secrets no repositório (Settings → Secrets):
- `GHCR_TOKEN` / `GITHUB_TOKEN` (quando necessário para GHCR)
- `MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` (usados pelos jobs que criam o MySQL em tempo de execução)
- `KUBECONFIG_BASE64` (opcional, quando deployments para k8s são necessários via CI)

Os workflows foram escritos para checar a presença dessas variáveis antes de tentar operações sensíveis (login/push/deploy) — isso evita falhas em forks ou em execuções sem secrets.

## GUI no Windows (VcXsrv / XLaunch)

Para executar a interface Tkinter a partir do container no Windows:
3. Execute o compose GUI:

```powershell
docker compose -f docker-compose.gui.yml up --build
```

O compose já define `DISPLAY=host.docker.internal:0.0` — se você usa WSL2, a configuração pode variar e pode ser necessário usar o IP do host em vez de `host.docker.internal`.

## Troubleshooting rápido

- "No tests ran": verifique se os testes estão no diretório `tests/` e se o nome de arquivo segue o padrão `test_*.py` ou `*_test.py`. Use `python -m unittest discover -v tests` localmente para debugar.
- Erros de push para GHCR: verifique se o owner/repo está em minúsculas e se o token tem permissão `packages:write`.
- MySQL no CI não fica pronto: os workflows incluem um loop de espera; localmente verifique `docker logs <mysql-container>` para ver erros de inicialização.
- GUI: "no display name and no $DISPLAY environment variable" significa que o container não recebeu a variável `DISPLAY` — use `docker-compose.gui.yml` e rode um X Server (VcXsrv).

## Resumo final

Este README documenta o fluxo principal do projeto, os workflows de CI/CD e como executar o projeto localmente com Docker Compose (incluindo GUI via X forwarding) e com Kubernetes.
## Como rodar localmente

1. Instale o MySQL e crie o banco `sistema_escolar`.
2. Instale as dependências:
	```
	pip install -r requirements.txt
	pip install mysql-connector-python pulp
	```
3. Execute o sistema:
	```
	python school_schedule.py
	```

## Testes

Para rodar os testes:
```
python -m unittest tests/test_schedule.py -v
```

## Docker

O projeto inclui um `Dockerfile` para facilitar a execução em ambientes isolados. O Dockerfile utiliza a imagem `python:3.13-slim`, instala as dependências e executa o sistema.

### Como usar o Docker

1. Certifique-se de que o MySQL esteja rodando e acessível para o container (ajuste variáveis de conexão se necessário).
2. Construa a imagem Docker:
	```
	docker build -t school-scheduler .
	```
3. Execute o container:
	```
	docker run --rm -it school-scheduler
	```

Se precisar conectar o container ao banco MySQL local, pode ser necessário usar a opção `--network host` (Linux) ou mapear portas e ajustar o `DB_HOST` para o IP da máquina.

> **Observação:** O sistema utiliza interface gráfica (Tkinter). Para rodar o container com interface gráfica, é necessário configurar o acesso ao servidor X (Linux) ou usar soluções específicas para Windows/macOS. Para uso em modo headless (sem interface), o sistema imprime mensagens no console.