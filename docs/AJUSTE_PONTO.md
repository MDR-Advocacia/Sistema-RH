# Manual de Funcionalidade: Módulo de Ajuste de Ponto

## 1. Visão Geral

O Módulo de Ajuste de Ponto permite que o RH solicite correções em registros de ponto específicos de um colaborador. O sistema facilita a comunicação, a coleta de justificativas e a gestão dos documentos assinados, mantendo um histórico completo e em conformidade com a LGPD.

---

## 2. Fluxo para o Administrador (RH)

### 2.1. Solicitando um Ajuste de Ponto

1.  No menu lateral, clique em **"Funcionários"** e acesse o perfil completo do colaborador desejado.
2.  Dentro do perfil, clique na aba **"Controle de Ponto"**.
3.  Na seção **"Solicitar Ajuste de Ponto"**:
    -   Selecione a **"Data do Ajuste"** em que ocorreu a inconsistência.
    -   Escolha o **"Tipo de Ajuste"** (`Entrada no escritório`, `Saída para o intervalo`, etc.).
    -   Clique em **"Criar Pendência"**.

Uma pendência será criada para o colaborador, que será notificado por e-mail.

### 2.2. Gerenciando Ajustes Enviados

Quando um colaborador envia um ajuste preenchido, ele aparece na tela de gestão centralizada.

1.  No menu lateral, clique em **"Gestão de Ponto"**.
2.  A página exibirá uma lista de todos os ajustes que foram enviados e estão aguardando revisão.
3.  Para cada item, o RH pode:
    -   **Visualizar:** Baixar o documento assinado pelo colaborador para conferência.
    -   **Aprovar:** Se o ajuste estiver correto, o RH clica em "Aprovar". O status da solicitação muda para "Aprovado" e a pendência é encerrada.
    -   **Reprovar:** Se houver um problema, o RH clica em "Reprovar". Uma janela exigirá o **motivo da reprovação**. A pendência retornará ao colaborador com a observação do RH.

### 2.3. Ações no Perfil do Colaborador

Na aba **"Controle de Ponto"** do perfil de um funcionário, o RH também pode:
-   Visualizar o histórico completo de todos os ajustes solicitados para aquele colaborador.
-   Baixar os documentos já aprovados.
-   **Remover** uma solicitação que foi criada por engano (clicando no ícone de lixeira).

---

## 3. Fluxo para o Colaborador

### 3.1. Respondendo a uma Solicitação

1.  Ao acessar a **Dashboard**, o colaborador verá um card chamado **"Ajustes de Ponto Pendentes"**.
2.  A pendência informará a **data** e o **tipo de ajuste** solicitado.
3.  O colaborador clica no botão **"Responder"**.

### 3.2. Preenchendo a Justificativa

Na janela (modal) que se abre, o colaborador deve seguir os seguintes passos:

1.  **Preencher a Justificativa:** Escrever no campo de texto o motivo detalhado para o ajuste solicitado.
2.  **Baixar o Modelo:** Clicar no botão **"Baixar Modelo Pré-Preenchido (.docx)"**. O sistema irá gerar e baixar um arquivo Word já com o nome, cargo, data e a justificativa preenchidos.
3.  **Salvar como PDF e Assinar:** O colaborador deve abrir o arquivo `.docx`, salvá-lo como PDF e usar um assinador digital (como o do GOV.BR) para assinar o documento.
4.  **Anexar o PDF Assinado:** De volta ao sistema, o colaborador clica em "Selecione o arquivo" e anexa o **PDF assinado**.
5.  **Enviar para Revisão:** Clicar no botão final para enviar o ajuste ao RH.

A pendência desaparecerá da sua dashboard e aguardará a aprovação do RH. Se for reprovada, ela reaparecerá com a justificativa do RH para correção.