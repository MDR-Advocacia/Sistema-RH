# Manual de Funcionalidade: Integração com Active Directory (AD)

## 1. Visão Geral

A integração do MDRH com o Active Directory (AD) da empresa foi projetada para criar um ecossistema de gerenciamento de identidades seguro e automatizado. O sistema opera em duas vias principais, tratando o MDRH como a fonte da verdade para os dados cadastrais e o AD como a fonte da verdade para a autenticação.

1. **Provisionamento (MDRH → AD):** O ciclo de vida de um colaborador (criação, atualização, desligamento) gerenciado no MDRH é automaticamente espelhado no Active Directory.
2. **Autenticação e Vinculação (AD → MDRH):** O login no sistema é feito primariamente contra o AD, garantindo uma senha única e centralizada para o colaborador.
---

## 2. Provisionamento de Usuários (MDRH → AD)

Este fluxo ocorre quando um administrador do RH realiza ações dentro do sistema MDRH.

### 2.1. Criação de Usuário

1.  QQuando um administrador do RH cadastra um **"Novo Funcionário"** através do formulário no MDRH:
    -   O sistema primeiramente cria os registros  **`Funcionario`** e **`Usuario`** no banco de dados local.
    -   O sistema se conecta ao AD e cria uma nova conta de usuário na pasta `Users`.
    -   Os dados preenchidos (Nome Completo, Cargo, Setor) são sincronizados com os campos correspondentes no AD (`displayName`, `title`, `department`).
    -   Uma senha inicial padrão (`AD_DEFAULT_PASSWORD` definida no `.env`) é atribuída à conta no AD.
    -   A conta é criada como **ATIVADA** e com a flag **"O usuário deve alterar a senha no próximo logon"** marcada.

### 2.2. Atualização de Usuário

1.  Quando o RH **edita o cadastro** de um funcionário no MDRH (pela tela "Editar Cadastro"), as alterações são automaticamente espelhadas no AD.
2.  Campos sincronizados:
    -   **Nome Completo:** Se o nome for alterado, o sistema renomeia o objeto do usuário e atualiza o "Nome de Exibição" no AD.
    -   **Cargo e Setor:** Os campos de título e departamento no AD são atualizados.

### 2.3. Desligamento e Suspensão

1.  **Suspender:** Quando o RH clica em **"Suspender"** no perfil do funcionário, a conta correspondente no AD é imediatamente **desativada** (disabled).
2.  **Reativar:** Ao clicar em **"Reativar"**, a conta no AD é **ativada** novamente (enabled).
3.  **Desligar:** A ação de **"Desligar"** executa um processo de offboarding:.
    - A conta no AD é permanentemente **desativada**.
    - Dados pessoais sensíveis no banco de dados do MDRH são **anonimizados** para conformidade com a LGPD.

---

## 3. Autenticação e Vinculação (Fluxo: Usuário para o Sistema)

Este fluxo ocorre quando qualquer colaborador tenta fazer login no sistema.

### 3.1. Fluxo de Login

1.  O usuário acessa a tela de login do MDRH e insere seu **Usuário de Rede** (ex: `pedro.alecrim`) e sua **senha do AD** (a mesma que usa para logar no computador).
2.  O sistema MDRH tenta se autenticar diretamente no Active Directory com as credenciais fornecidas.
3.  Se a autenticação no AD for bem-sucedida, o sistema prossegue para a vinculação.
4.  **Fallback:** Se a conexão com o AD falhar (servidor offline, etc.), o sistema tenta uma autenticação secundária no banco de dados local. Isso garante que administradores com contas locais (criadas via comando create-admin) possam sempre acessar o sistema para manutenção.

### 3.2. Vinculação e Provisionamento Just-in-Time
Após uma autenticação bem-sucedida no AD, o sistema verifica a situação do usuário no banco de dados local:

-   **Cenário 1: Vinculação (Usuário AD já tem cadastro no RH):** Se um usuário do AD faz login pela primeira vez e o sistema encontra um `Funcionário` no banco de dados com o mesmo nome completo, ele automaticamente cria a conta de `Usuario` no sistema e a vincula ao cadastro existente.
-   **Cenário 2: Provisionamento (Usuário AD não tem cadastro no RH):** Se um usuário do AD faz login e não há um funcionário correspondente, o sistema cria um cadastro básico de `Funcionario` para ele.
-   **Cenário 3 (Provisionamento Just-in-Time):** Se o usuário do AD não existe no MDRH e não há nenhum funcionário com nome correspondente, o sistema cria um novo cadastro básico de Funcionario e um novo Usuario para ele. Este cenário é útil para novos colaboradores que ainda não foram formalmente cadastrados pelo RH.
-   **Cenário 4: Fallback Local:** Se a autenticação com o AD falhar (por qualquer motivo, como o servidor estar offline), o sistema tenta validar as credenciais no banco de dados local. Isso garante que os administradores de sistema (como `admin@sistema.com`) sempre consigam acessar o MDRH.