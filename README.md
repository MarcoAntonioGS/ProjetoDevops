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
# School Scheduler

Este projeto é um sistema de agendamento escolar que utiliza Python, MySQL e PuLP para otimizar cronogramas de professores, matérias e turmas. Ele possui uma interface gráfica (Tkinter) para cadastro e visualização dos dados, além de uma pipeline CI/CD automatizada via GitHub Actions.

## Funcionalidades

- Cadastro de professores, matérias e turmas.
- Otimização automática do cronograma escolar usando programação linear (PuLP).
- Interface gráfica para inserção e consulta dos dados.
- Armazenamento dos dados em banco MySQL.
- Testes automatizados para garantir o funcionamento do sistema.

## Estrutura do Projeto

- `school_schedule.py`: Código principal do sistema, incluindo a interface gráfica, funções de banco de dados e otimização.
- `tests/test_schedule.py`: Testes unitários para validar conexão, inserção de dados e otimização do cronograma.
- `requirements.txt`: Dependências do projeto (mysql-connector-python, pulp, etc).
- `Dockerfile`: (Opcional) Para empacotamento do projeto.
- `.github/workflows/ci-cd.yml`: Pipeline CI/CD para automação de testes e build.

## Como funciona o código

1. **Conexão com MySQL**: O sistema conecta-se ao banco de dados MySQL usando credenciais definidas no código ou via variáveis de ambiente.
2. **Criação de Tabelas**: As tabelas necessárias são criadas automaticamente se não existirem.
3. **Interface Gráfica**: Usuários podem cadastrar professores, matérias e turmas, e visualizar os dados.
4. **Otimização**: Ao clicar em "Gerar Cronograma Otimizado", o sistema utiliza PuLP para distribuir aulas de forma eficiente, respeitando disponibilidade e carga horária.
5. **Exibição**: O cronograma gerado é exibido na interface.

## Pipeline CI/CD

A pipeline está definida em `.github/workflows/ci-cd.yml` e realiza os seguintes passos:

1. **Disparo**: Executa em pushes ou pull requests para os branches `main` ou `master`.
2. **Serviço MySQL**: Inicializa um container MySQL para testes.
3. **Configuração do Python**: Instala o Python 3.13 e dependências do projeto.
4. **Testes**: Executa os testes unitários do projeto, validando conexão, inserção e otimização.
5. **Build e Deploy**: (Simulado) Exibe mensagens de build e deploy.

Variáveis sensíveis, como senha do banco, são passadas via GitHub Secrets.

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
