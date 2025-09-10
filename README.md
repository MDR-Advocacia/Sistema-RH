# MDRH - Sistema de Gestão de Recursos Humanos

## 📖 Sobre o Projeto
O **MDRH** é um sistema de gestão de RH interno, projetado para centralizar e automatizar processos essenciais do departamento.  
A aplicação é construída com **Python** e **Flask**, rodando em um ambiente totalmente containerizado com **Docker** e utilizando **PostgreSQL** como banco de dados, garantindo portabilidade, segurança e escalabilidade.

O sistema está integrado com o **Active Directory (AD)** para autenticação centralizada e provisionamento automático de usuários, alinhando-se com as melhores práticas de gestão de identidade em ambientes corporativos.

---

## ✨ Funcionalidades Principais

### Gestão de Colaboradores
- Cadastro, edição, visualização e listagem de funcionários.  
- Filtro de colaboradores por status: **Ativos, Suspensos e Desligados**.  
- Sincronização de status (suspender/reativar) com o **Active Directory**.  
- Processo de **Offboarding** (Desligamento) com anonimização de dados pessoais para conformidade com a **LGPD**.  

### Autenticação e Segurança
- Integração com Active Directory (**LDAP**): Autenticação centralizada usando as credenciais de rede.  

### Provisionamento Automático
- Ao criar um funcionário no MDRH, a conta é automaticamente criada e ativada no AD.  
- Ao editar um funcionário (nome, cargo, setor), as alterações são espelhadas no AD.  
- **Vinculação Inteligente**: Usuários existentes no AD que fazem login pela primeira vez são automaticamente vinculados aos seus perfis de funcionário no sistema.  
- **Autenticação Local de Fallback**: Contas de administrador locais continuam funcionando, garantindo acesso ao sistema mesmo se o AD estiver offline.  

### Pipeline de Documentação Inteligente
- **Cadastro de Tipos de Documento**: O RH pode configurar quais documentos são necessários e marcá-los como obrigatórios na admissão.  
- **Onboarding Automático**: O sistema cria automaticamente as pendências de documentos obrigatórios para novos funcionários no primeiro login.  
- **Solicitação em Lote**: O RH pode solicitar um documento específico para múltiplos funcionários de uma só vez.  

### Módulos de RH
- **Mural de Avisos**: Publicação de comunicados gerais com suporte a anexos e log de ciência.  
- **Ajuste de Ponto**: Fluxo de solicitação (individual e em lote), preenchimento de justificativa, geração de documento `.docx` pré-preenchido, envio para aprovação e gestão pelo RH.  
- **Canal de Denúncias Anônimas**: Canal seguro para relatos, com geração de protocolo para acompanhamento.  

### Conformidade com LGPD
- Coleta de **consentimento explícito** dos termos de uso e política de privacidade.  
- **Barreira de navegação** que impede o uso do sistema antes do consentimento.  
- **Anonimização** de dados pessoais de funcionários desligados.  

### DevOps e Resiliência
- **Ambiente Containerizado**: Aplicação e banco de dados rodando em containers Docker isolados.  
- **Backups Automatizados**: Serviço dedicado que realiza backups diários do banco de dados PostgreSQL.  
- **Política de Retenção**: Backups são mantidos por 7 dias, com limpeza automática dos mais antigos.  

---

## 🛠️ Tecnologias Utilizadas
- **Backend**: Python 3.11+, Flask  
- **Banco de Dados**: PostgreSQL 16  
- **Ambiente**: Docker, Docker Compose  
- **Integrações**: LDAP (Active Directory)  
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5  
- **Bibliotecas Principais**: SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Mail, ldap3, docxtpl  

---

## 🚀 Instalação e Execução

### Pré-requisitos
- **Docker** e **Docker Compose** instalados e em execução.  

### 1. Configuração do Ambiente
Crie o arquivo de ambiente:  
Na raiz do projeto, crie um arquivo chamado **`.env`**.

Preencha o arquivo **.env** com suas configurações.  
Exemplo:  

```env
SECRET_KEY=gere_uma_chave_longa_e_aleatoria_aqui

POSTGRES_USER=admin
POSTGRES_PASSWORD=%mdr.123%
POSTGRES_DB=mdrh_db

MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=seu-email-de-sistema@gmail.com
MAIL_PASSWORD=sua_senha_de_app_de_16_digitos
MAIL_SENDER="MDRH seu-email-de-sistema@gmail.com"

LDAP_HOST=ldaps://192.168.0.31
LDAP_PORT=636
LDAP_BASE_DN=DC=mdr,DC=local
LDAP_USERS_DN=CN=Users,DC=mdr,DC=local
LDAP_BIND_USER_DN=CN=interno,OU=Serviços,DC=mdr,DC=local
LDAP_BIND_USER_PASSWORD=senha_da_conta_de_servico
AD_DEFAULT_PASSWORD=Mudar@12345
```

### 2. Execução com Docker Compose

1.  **Construa e Inicie os Containers:**
    Abra um terminal na raiz do projeto e execute o comando:
    `docker-compose up --build -d`
    *(A flag `-d` executa os containers em segundo plano)*.

2.  **Crie as Tabelas no Banco de Dados:**
    Aguarde alguns segundos para o container do PostgreSQL iniciar e então execute:
    `docker-compose exec web flask db upgrade`

3.  **Crie seu Usuário Administrador Local:**
    Este usuário não depende do AD e serve como acesso de emergência.
    `docker-compose exec web flask create-admin seu-email@dominio.com sua-senha-segura`

4.  **Acesse a Aplicação:**
    Abra seu navegador e acesse `http://127.0.0.1:5000`.

### 3. (Opcional) Restaurar Dados de um Backup

Se você possui um backup (`.json`), pode restaurar os dados após o passo 2 (`flask db upgrade`).

`docker-compose exec web python restore.py`

---

## 🔧 Operações e Manutenção

-   **Ver Logs da Aplicação em Tempo Real:**
    `docker-compose logs -f web`

-   **Executar um Backup Manual:**
    `docker-compose run --rm backup`

-   **Listar Backups Existentes:**
    `docker-compose run --rm --entrypoint ls backup -l /backups`

-   **Baixar um Arquivo de Backup:**
    Consulte o `MANUAL_OPERACOES.md` para o passo a passo detalhado.

---

## 📁 Estrutura do Projeto

```

├── app/                  # Contém toda a lógica da aplicação Flask
├── migrations/           # Arquivos de migração do banco de dados (gerados)
├── scripts/              # Scripts de utilidades (ex: backup.sh)
├── static/               # Arquivos estáticos (CSS, JS, Imagens, Modelos .docx)
├── templates/            # Arquivos HTML (Jinja2)
├── uploads/              # (Gerado) Pasta para uploads de arquivos (fotos, documentos)
├── .env                  # Arquivo de variáveis de ambiente (NÃO VERSIONADO)
├── docker-compose.yml    # Orquestração dos containers
├── Dockerfile            # Receita para construir a imagem da aplicação
├── requirements.txt      # Dependências Python
└── run.py                # Ponto de entrada da aplicação
```