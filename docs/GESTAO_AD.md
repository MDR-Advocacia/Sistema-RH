# Manual de Funcionalidade: Integração com Active Directory (AD)

## 1. Visão Geral

O sistema MDRH está integrado ao Active Directory (AD) da empresa para centralizar a gestão de identidades e automatizar o ciclo de vida dos usuários, seguindo as melhores práticas de segurança. A integração funciona em duas vias principais: **Provisionamento (MDRH → AD)** e **Autenticação (Sistema → AD)**.

---

## 2. Provisionamento de Usuários (MDRH → AD)

O sistema de RH é a **fonte da verdade** para os dados cadastrais dos colaboradores.

### 2.1. Criação de Usuário

1.  Quando um administrador do RH cadastra um **"Novo Funcionário"** no sistema MDRH, uma série de ações automáticas são disparadas:
    -   O sistema gera um nome de usuário padronizado no formato **`nome.sobrenome`**.
    -   O sistema se conecta ao AD e cria uma nova conta de usuário na pasta `Users`.
    -   Os dados preenchidos no formulário (Nome Completo, Cargo, Setor) são sincronizados com os campos correspondentes no AD.
    -   Uma senha inicial (fornecida no formulário) é definida para o usuário no AD.
    -   A conta é criada como **ATIVADA** e com a flag **"O usuário deve alterar a senha no próximo logon"** marcada.

### 2.2. Atualização de Usuário

1.  Quando o RH **edita o cadastro** de um funcionário no MDRH (pela tela "Editar Cadastro"), as alterações são automaticamente espelhadas no AD.
2.  Campos sincronizados:
    -   **Nome Completo:** Se o nome for alterado, o sistema renomeia o objeto do usuário e atualiza o "Nome de Exibição" no AD.
    -   **Cargo e Setor:** Os campos de título e departamento no AD são atualizados.

### 2.3. Desligamento e Suspensão

1.  **Suspender:** Quando o RH clica em **"Suspender"** no perfil do funcionário, a conta correspondente no AD é **desativada** (disabled).
2.  **Reativar:** Ao clicar em **"Reativar"**, a conta no AD é **ativada** novamente (enabled).
3.  **Desligar:** A ação de **"Desligar"** também **desativa** permanentemente a conta no AD.
4.  **Remover:** Ao remover um funcionário do MDRH, o objeto do usuário correspondente é **excluído** do Active Directory.

---

## 3. Autenticação Centralizada (Sistema → AD)

O Active Directory é a **fonte da verdade** para as senhas e a autenticação.

### 3.1. Fluxo de Login

1.  O usuário acessa a tela de login do MDRH e insere seu **Usuário de Rede** (`nome.sobrenome`) e sua **senha do AD** (a mesma que usa para logar no computador).
2.  O sistema MDRH se conecta ao AD e valida as credenciais.
3.  Se a autenticação no AD for bem-sucedida, o sistema procura um usuário com o e-mail correspondente (`nome.sobrenome@mdr.local`) em seu banco de dados local.

### 3.2. Vinculação e Provisionamento Just-in-Time

-   **Cenário 1: Vinculação (Usuário AD já tem cadastro no RH):** Se um usuário do AD faz login pela primeira vez e o sistema encontra um `Funcionário` no banco de dados com o mesmo nome completo, ele automaticamente cria a conta de `Usuario` no sistema e a vincula ao cadastro existente.
-   **Cenário 2: Provisionamento (Usuário AD não tem cadastro no RH):** Se um usuário do AD faz login e não há um funcionário correspondente, o sistema cria um cadastro básico de `Funcionario` para ele.
-   **Cenário 3: Fallback Local:** Se a autenticação com o AD falhar (por qualquer motivo, como o servidor estar offline), o sistema tenta validar as credenciais no banco de dados local. Isso garante que os administradores de sistema (como `admin@sistema.com`) sempre consigam acessar o MDRH.