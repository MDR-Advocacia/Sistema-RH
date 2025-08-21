# MDRH - Sistema de Gestão de Recursos Humanos

## 📖 Sobre o Projeto

O **MDRH** é um sistema de gestão de RH interno, projetado para centralizar e automatizar processos essenciais do departamento. A aplicação é construída com Python e Flask, rodando em um ambiente totalmente containerizado com Docker e utilizando PostgreSQL como banco de dados, garantindo portabilidade, segurança e escalabilidade.

O sistema está integrado com o **Active Directory (AD)** para autenticação centralizada e provisionamento automático de usuários, alinhando-se com as melhores práticas de gestão de identidade em ambientes corporativos.

---

## ✨ Funcionalidades Principais

- **Gestão de Colaboradores:**
  - Cadastro, edição, visualização e listagem de funcionários.
  - Filtro de colaboradores por status: Ativos, Suspensos e Desligados.
  - Sincronização de status (suspender/reativar) com o Active Directory.
  - Processo de **Offboarding (Desligamento)** com anonimização de dados pessoais para conformidade com a LGPD.

- **Autenticação e Segurança:**
  - **Integração com Active Directory (LDAP):** Autenticação centralizada usando as credenciais de rede (`nome.sobrenome`).
  - **Provisionamento Automático:**
    - Ao criar um funcionário no MDRH, a conta é automaticamente criada e ativada no AD.
    - Ao editar um funcionário (nome, cargo, setor), as alterações são espelhadas no AD.
    - Ao excluir um funcionário no MDRH, a conta é removida do AD.
  - **Vinculação Inteligente:** Usuários existentes no AD que fazem login pela primeira vez são automaticamente vinculados aos seus perfis de funcionário no sistema (baseado no nome completo).
  - **Autenticação Local de Fallback:** Contas de administrador locais continuam funcionando, garantindo acesso ao sistema mesmo se o AD estiver offline.
  - **Gestão de Senhas:** Redefinição de senha para usuários locais e forçar a alteração de senha no primeiro login para usuários criados via MDRH.

- **Módulos de RH:**
  - **Mural de Avisos:** Publicação de comunicados gerais com suporte a anexos e log de ciência.
  - **Gestão de Documentos:** Upload e armazenamento de documentos por colaborador.
  - **Ajuste de Ponto:** Fluxo de solicitação, preenchimento de justificativa, geração de documento `.docx` pré-preenchido, envio para aprovação e gestão pelo RH.

- **Conformidade com LGPD:**
  - Coleta de consentimento explícito dos termos de uso e política de privacidade.
  - Barreira de navegação que impede o uso do sistema antes do consentimento.
  - Anonimização de dados pessoais de funcionários desligados.

- **DevOps e Resiliência:**
  - **Ambiente Containerizado:** Aplicação e banco de dados rodando em containers Docker isolados.
  - **Backups Automatizados:** Serviço dedicado que realiza backups diários do banco de dados PostgreSQL.
  - **Política de Retenção:** Backups são mantidos por 7 dias, com limpeza automática dos mais antigos.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.11+, Flask
- **Banco de Dados:** PostgreSQL 16
- **Ambiente:** Docker, Docker Compose
- **Integrações:** LDAP (Active Directory)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Bibliotecas Principais:** SQLAlchemy, Flask-Migrate, Flask-Login, Flask-Mail, ldap3, docxtpl.

---

## 🚀 Instalação e Execução

### Pré-requisitos

-   [Docker](https://www.docker.com/products/docker-desktop/) instalado e em execução.

### 1. Configuração do Ambiente

1.  **Copie o Arquivo de Ambiente:**
    Crie uma cópia do arquivo `.env.example` (se existir) ou crie um novo arquivo chamado `.env` na raiz do projeto.

2.  **Preencha o Arquivo `.env`:**
    Abra o arquivo `.env` e preencha todas as variáveis com as suas configurações.

    ```
    # Chave secreta para a segurança da sessão do Flask
    SECRET_KEY=gere_uma_chave_longa_e_aleatoria_aqui

    # Credenciais do Banco de Dados PostgreSQL
    POSTGRES_USER=mdrh_user
    POSTGRES_PASSWORD=uma_senha_muito_forte_123
    POSTGRES_DB=mdrh_db

    # Configurações de E-mail (Ex: Gmail com Senha de App)
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USERNAME=seu-email-de-sistema@gmail.com
    MAIL_PASSWORD=sua_senha_de_app_de_16_digitos
    MAIL_SENDER="MDRH <seu-email-de-sistema@gmail.com>"

    # Configurações do Active Directory (LDAP)
    LDAP_HOST=192.168.0.31
    LDAP_PORT=389
    LDAP_BASE_DN=DC=mdr,DC=local
    LDAP_USER_OU=CN=Users,DC=mdr,DC=local
    LDAP_BIND_USER_DN=CN=interno,OU=Serviços,DC=mdr,DC=local
    LDAP_BIND_USER_PASSWORD=senha_da_conta_de_servico
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
Com certeza! Um README.md bem escrito é o cartão de visita de um projeto. Ele deve ser claro, completo e guiar qualquer novo desenvolvedor (ou você mesmo, no futuro) a entender e rodar o sistema sem dificuldades.

Preparei uma reestruturação completa do seu README.md para refletir o estado atual e profissional do projeto, incluindo a migração para Docker e PostgreSQL, a integração com o AD e as práticas de DevOps que implementamos.

Aqui está o conteúdo completo. Você pode copiar este bloco de código e colar diretamente no seu arquivo README.md.

Markdown

# MDRH - Sistema de Gestão de Recursos Humanos

## 📖 Sobre o Projeto

O **MDRH** é um sistema de gestão de RH interno, projetado para centralizar e automatizar processos essenciais do departamento. A aplicação é construída com Python e Flask, rodando em um ambiente totalmente containerizado com Docker e utilizando PostgreSQL como banco de dados, garantindo portabilidade, segurança e escalabilidade.

O sistema está integrado com o **Active Directory (AD)** para autenticação centralizada e provisionamento automático de usuários, alinhando-se com as melhores práticas de gestão de identidade em ambientes corporativos.

---

## ✨ Funcionalidades Principais

- **Gestão de Colaboradores:**
  - Cadastro, edição, visualização e listagem de funcionários.
  - Filtro de colaboradores por status: Ativos, Suspensos e Desligados.
  - Sincronização de status (suspender/reativar) com o Active Directory.
  - Processo de **Offboarding (Desligamento)** com anonimização de dados pessoais para conformidade com a LGPD.

- **Autenticação e Segurança:**
  - **Integração com Active Directory (LDAP):** Autenticação centralizada usando as credenciais de rede (`nome.sobrenome`).
  - **Provisionamento Automático:**
    - Ao criar um funcionário no MDRH, a conta é automaticamente criada e ativada no AD.
    - Ao editar um funcionário (nome, cargo, setor), as alterações são espelhadas no AD.
    - Ao excluir um funcionário no MDRH, a conta é removida do AD.
  - **Vinculação Inteligente:** Usuários existentes no AD que fazem login pela primeira vez são automaticamente vinculados aos seus perfis de funcionário no sistema (baseado no nome completo).
  - **Autenticação Local de Fallback:** Contas de administrador locais continuam funcionando, garantindo acesso ao sistema mesmo se o AD estiver offline.
  - **Gestão de Senhas:** Redefinição de senha para usuários locais e forçar a alteração de senha no primeiro login para usuários criados via MDRH.

- **Módulos de RH:**
  - **Mural de Avisos:** Publicação de comunicados gerais com suporte a anexos e log de ciência.
  - **Gestão de Documentos:** Upload e armazenamento de documentos por colaborador.
  - **Ajuste de Ponto:** Fluxo de solicitação, preenchimento de justificativa, geração de documento `.docx` pré-preenchido, envio para aprovação e gestão pelo RH.

- **Conformidade com LGPD:**
  - Coleta de consentimento explícito dos termos de uso e política de privacidade.
  - Barreira de navegação que impede o uso do sistema antes do consentimento.
  - Anonimização de dados pessoais de funcionários desligados.

- **DevOps e Resiliência:**
  - **Ambiente Containerizado:** Aplicação e banco de dados rodando em containers Docker isolados.
  - **Backups Automatizados:** Serviço dedicado que realiza backups diários do banco de dados PostgreSQL.
  - **Política de Retenção:** Backups são mantidos por 7 dias, com limpeza automática dos mais antigos.

---

## 🛠️ Tecnologias Utilizadas

- **Backend:** Python 3.11+, Flask
- **Banco de Dados:** PostgreSQL 16
- **Ambiente:** Docker, Docker Compose
- **Integrações:** LDAP (Active Directory)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Bibliotecas Principais:** SQLAlchemy, Flask-Migrate, Flask-Login, Flask-Mail, ldap3, docxtpl.

---

## 🚀 Instalação e Execução

### Pré-requisitos

-   [Docker](https://www.docker.com/products/docker-desktop/) instalado e em execução.

### 1. Configuração do Ambiente

1.  **Copie o Arquivo de Ambiente:**
    Crie uma cópia do arquivo `.env.example` (se existir) ou crie um novo arquivo chamado `.env` na raiz do projeto.

2.  **Preencha o Arquivo `.env`:**
    Abra o arquivo `.env` e preencha todas as variáveis com as suas configurações.

    ```
    # Chave secreta para a segurança da sessão do Flask
    SECRET_KEY=gere_uma_chave_longa_e_aleatoria_aqui

    # Credenciais do Banco de Dados PostgreSQL
    POSTGRES_USER=mdrh_user
    POSTGRES_PASSWORD=uma_senha_muito_forte_123
    POSTGRES_DB=mdrh_db

    # Configurações de E-mail (Ex: Gmail com Senha de App)
    MAIL_SERVER=smtp.gmail.com
    MAIL_PORT=587
    MAIL_USE_TLS=True
    MAIL_USERNAME=seu-email-de-sistema@gmail.com
    MAIL_PASSWORD=sua_senha_de_app_de_16_digitos
    MAIL_SENDER="MDRH <seu-email-de-sistema@gmail.com>"

    # Configurações do Active Directory (LDAP)
    LDAP_HOST=192.168.0.31
    LDAP_PORT=389
    LDAP_BASE_DN=DC=mdr,DC=local
    LDAP_USER_OU=CN=Users,DC=mdr,DC=local
    LDAP_BIND_USER_DN=CN=interno,OU=Serviços,DC=mdr,DC=local
    LDAP_BIND_USER_PASSWORD=senha_da_conta_de_servico
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