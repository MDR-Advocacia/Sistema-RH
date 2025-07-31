# Documentação do Projeto: Sistema de RH (MDRH)

## 1. Visão Geral

O MDRH é um sistema de gestão de Recursos Humanos desenvolvido para uso interno, com o objetivo de centralizar e otimizar as operações do departamento de RH, TI e Departamento Pessoal. A plataforma web, construída com a stack tecnológica Python/Flask, oferece um ambiente seguro e multifuncional para gerenciar colaboradores, comunicações internas, documentos e outras tarefas administrativas.

## 2. Tecnologias Utilizadas

O sistema é construído sobre uma base de tecnologias modernas e robustas, garantindo escalabilidade e manutenibilidade.

* **Backend:**
    * **Python 3.13:** Linguagem principal do projeto.
    * **Flask:** Micro-framework web para a construção da aplicação e da API.
    * **Flask-SQLAlchemy:** ORM (Object-Relational Mapper) para interação com o banco de dados.
    * **Flask-Migrate (Alembic):** Ferramenta para gerenciamento de migrações do esquema do banco de dados.
    * **Flask-Login:** Gerenciamento de sessões de usuário e autenticação.
    * **Werkzeug:** Ferramentas essenciais para aplicações WSGI, incluindo a segurança de senhas.
* **Banco de Dados:**
    * **SQLite:** Banco de dados padrão para o ambiente de desenvolvimento, pela sua simplicidade e portabilidade.
    * **PostgreSQL:** Recomendado para o ambiente de produção devido à sua robustez (a aplicação está pronta para a migração).
* **Frontend:**
    * **HTML5 / CSS3:** Estrutura e estilização das páginas.
    * **Bootstrap 5:** Framework de componentes para a criação de uma interface responsiva e moderna.
    * **JavaScript (Vanilla):** Utilizado para interatividade no lado do cliente, como a abertura de modais e requisições AJAX para a API.
    * **Jinja2:** Motor de templates do Flask, para renderização dinâmica das páginas.
* **Dependências Adicionais:**
    * **python-dotenv:** Para gerenciamento de variáveis de ambiente.
    * **pytz:** Para manipulação de fusos horários.
    * A lista completa pode ser encontrada no arquivo `requirements.txt`.

## 3. Estrutura do Projeto

O projeto segue uma estrutura modular e organizada para facilitar o desenvolvimento e a manutenção.

```
V2-sis-rh/
├── app/                  # Contém o núcleo da aplicação
│   ├── init.py       # Inicializa a aplicação Flask, extensões e blueprints
│   ├── auth.py           # Rotas de autenticação (login, logout, troca de senha)
│   ├── config.py         # Configurações da aplicação
│   ├── decorators.py     # Decoradores customizados (ex: verificação de permissão)
│   ├── documentos.py     # Rotas para a gestão de documentos
│   ├── models.py         # Definição dos modelos do banco de dados (SQLAlchemy)
│   ├── perfil.py         # Rotas para o perfil do usuário
│   └── routes.py         # Rotas principais da aplicação (dashboard, CRUD de funcionários, avisos)
├── instance/
│   └── projetinho.db     # Arquivo do banco de dados SQLite
├── migrations/           # Arquivos de migração gerados pelo Flask-Migrate
├── static/
│   ├── custom_style.css  # Folha de estilo principal com a identidade visual
│   └── modelo_importacao.csv # Modelo para importação em lote
├── templates/
│   ├── auth/             # Templates de autenticação
│   ├── avisos/           # Templates do mural de avisos
│   ├── documentos/       # Templates da gestão de documentos
│   ├── funcionarios/     # Templates do CRUD de funcionários
│   ├── perfil/           # Template de edição de perfil
│   ├── base.html         # Template base com o menu lateral e estrutura principal
│   └── index.html        # Template da Dashboard
├── uploads/              # Pasta para armazenamento de arquivos (documentos, fotos)
│   └── fotos_perfil/
├── .env                  # Arquivo de variáveis de ambiente (não versionado)
├── manage.py             # Script para comandos customizados (criar admin, etc.)
├── requirements.txt      # Lista de dependências Python
└── run.py                # Ponto de entrada para executar a aplicação
```

## 4. Configuração e Instalação

Siga os passos abaixo para configurar o ambiente de desenvolvimento.

1.  **Clone o Repositório:**
    ```bash
    git clone [https://github.com/MDR-Advocacia/Sistema-RH.git](https://github.com/MDR-Advocacia/Sistema-RH.git)
    cd V2-sis-rh
    ```

2.  **Crie e Ative um Ambiente Virtual (Recomendado):**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure as Variáveis de Ambiente:**
    * Crie um arquivo chamado `.env` na raiz do projeto.
    * Copie o conteúdo abaixo para dentro dele:
        ```env
        DATABASE_URL=sqlite:///instance/projetinho.db
        FLASK_APP=run.py
        FLASK_ENV=development
        ```

5.  **Crie o Banco de Dados:**
    * Execute os comandos de migração para criar todas as tabelas:
        ```bash
        flask db upgrade
        ```

6.  **Crie o Primeiro Usuário Administrador:**
    * Use o comando customizado para criar seu usuário de acesso. Substitua com seu e-mail e senha.
        ```bash
        flask create-admin seu-email@exemplo.com sua-senha-segura
        ```

7.  **Execute a Aplicação:**
    ```bash
    flask run
    ```
    Acesse `http://127.0.0.1:5000` no seu navegador.

## 5. Funcionalidades Implementadas

### 5.1. Autenticação e Permissões
* **Login Seguro:** Autenticação baseada em e-mail e senha, com hash de senhas.
* **Senha Provisória:** Novos usuários (criados manualmente ou via CSV) recebem uma senha provisória e são forçados a alterá-la no primeiro acesso.
* **Controle de Acesso por Papel (RBAC):** O acesso às funcionalidades é controlado por permissões (`admin_rh`, `admin_ti`, `colaborador`). Um decorador customizado (`@permission_required`) protege as rotas.

### 5.2. Dashboard
* **Dashboard de Admin:** Exibe dados agregados, como o número total de funcionários e avisos publicados.
* **Dashboard Pessoal:** Disponível para todos os usuários (incluindo admins), exibe um painel com pendências pessoais, como avisos não lidos e solicitações de documentos.

### 5.3. Gestão de Funcionários (CRUD)
* **Cadastro Completo:** Formulário para adicionar novos colaboradores, incluindo seus dados pessoais, profissionais, contato de emergência e acesso ao sistema (senha e permissões).
* **Listagem e Busca:** Tabela com todos os funcionários, com busca dinâmica por nome, CPF ou setor.
* **Ordenação:** A lista pode ser ordenada alfabeticamente pelo nome do funcionário.
* **Visualização Detalhada:** Um modal exibe todas as informações de um funcionário, incluindo seus documentos e pendências, ao clicar em seu nome na lista.
* **Edição e Remoção (Individual e em Lote):**
    * Admins podem editar os dados de um funcionário em uma página dedicada.
    * Admins (`admin_rh` ou `admin_ti`) podem remover funcionários individualmente (pelo modal) ou em lote (selecionando múltiplos na tabela).
* **Importação/Exportação via CSV:** Admins podem adicionar múltiplos funcionários de uma vez através de um arquivo CSV, que já cria o acesso de usuário com uma senha padrão.

### 5.4. Mural de Avisos
* **Criação de Avisos:** Admins podem publicar comunicados para toda a empresa, com a opção de anexar múltiplos arquivos.
* **Ciência de Avisos:** Colaboradores devem marcar cada aviso como "ciente", e o sistema registra a data e hora da ciência.
* **Auditoria de Logs:** Admins podem visualizar, para cada aviso, a lista de colaboradores que já deram ciência e a lista dos que ainda estão pendentes.
* **Remoção de Avisos:** Admins podem excluir avisos, o que também remove todos os seus anexos e logs de ciência associados.

### 5.5. Gestão de Documentos
* **Upload de Documentos (pelo RH):** O RH pode anexar documentos ao perfil de qualquer funcionário.
* **Solicitação de Documentos:** O RH pode criar uma "requisição de documento" para um colaborador, que aparece como uma pendência em sua dashboard.
* **Resposta à Solicitação:** O colaborador pode responder a uma solicitação enviando o arquivo diretamente pela sua dashboard. O sistema automaticamente marca a pendência como "concluída".
* **Visualização Centralizada:** Na página de gestão de documentos de um funcionário, o RH pode ver tanto os arquivos já enviados quanto as solicitações ainda pendentes.

### 5.6. Perfil do Usuário
* **Edição de Dados:** Cada usuário pode editar suas próprias informações, como nome, apelido, telefone e contato de emergência.
* **Foto de Perfil:** Usuários podem fazer o upload de uma foto de perfil, que é exibida no menu lateral e em outras áreas do sistema.

## 6. Comandos de Gerenciamento

O arquivo `manage.py` fornece comandos de terminal úteis para a administração do sistema:

* **`flask create-admin <email> <senha>`**
    * Cria um novo usuário com permissões de `admin_rh` e `admin_ti`. Essencial para a configuração inicial do sistema.
* **`flask remove-admin <email>`**
    * Remove um usuário e seu registro de funcionário associado. Útil para manutenção e limpeza de dados.

## 7. Próximos Passos e Melhorias Futuras

O sistema possui uma base sólida que permite diversas expansões:

* **Módulo de Feedback:** Implementar a funcionalidade de registro de feedbacks (o modelo de dados `Feedback` já existe).
* **Controle de Ponto:** Criar um módulo para registro de ponto, cálculo de horas e gestão de faltas.
* **Gestão de Férias:** Desenvolver um fluxo de solicitação e aprovação de férias.
* **Notificações:** Enviar notificações por e-mail para novas solicitações de documentos ou avisos importantes.
* **Integração com PostgreSQL:** Migrar o banco de dados de SQLite para PostgreSQL no ambiente de produção para maior robustez.
