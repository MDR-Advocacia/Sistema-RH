# Manual de Funcionalidade: Gestão de Documentos

## 1. Visão Geral

O Módulo de Gestão de Documentos foi projetado para ser um pipeline inteligente e flexível, permitindo que o departamento de RH gerencie todo o ciclo de vida da documentação dos colaboradores, desde a admissão até solicitações pontuais.

O sistema opera com três pilares principais:

1. Configuração: O RH tem total autonomia para definir quais documentos são necessários.

2. Automação: O sistema cria automaticamente as pendências de admissão para novos colaboradores.

3. Gestão Ativa: O RH pode fazer solicitações manuais, tanto individuais quanto em lote, a qualquer momento.

---

## 2. Fluxo para o Administrador (RH)

### 2.1. Configurando os Tipos de Documento (Ação Inicial)

Antes de solicitar, o RH precisa definir a lista de todos os documentos que podem ser pedidos.

1.  No menu, acesse **Gestão de Documentos**..
2.  Clique no botão **Configurar Tipos de Documento** no canto superior direito da tela.
3.  Nesta nova página, você pode:
    - **Criar um Novo Tipo:** Clicando em "Novo Tipo", você pode cadastrar um documento (ex: "RG", "Comprovante de Endereço", "Certificado de Reservista").
    - **Marcar como Obrigatório:** Ao criar ou editar um tipo, marque a caixa "Obrigatório na Admissão?". Isso fará com que este documento seja solicitado automaticamente para todos os novos funcionários.
    - **Editar e Excluir:** Gerenciar os tipos de documento já existentes na tabela.


### 2.2. Onboarding de Novos Colaboradores (Fluxo Automático)

O sistema automatiza a solicitação de documentos de admissão.

1.  **Como funciona:** Quando um novo funcionário faz seu primeiro login no sistema, o MDRH consulta a lista de tipos de documento, identifica todos os que estão marcados como "Obrigatório na Admissão" e cria as pendências para o colaborador automaticamente..
2.  **Ação do RH**: Nenhuma. O processo é 100% automático.

Uma pendência será criada para o colaborador, e ele será notificado por e-mail.

### 2.3. Solicitando Documentos Manualmente (Individual ou em Lote)

Para demandas específicas (reciclagens, novas políticas, documentos de um setor, etc.), o RH pode fazer solicitações manuais.

1.  Acesse a tela de **"Gestão de Documentos"**.
2.  Vá para a aba **Solicitar Documento**.
3.  **Selecione o Documento:** No primeiro campo, escolha na lista o tipo de documento que deseja solicitar. A lista é populada com os tipos que você cadastrou no passo 2.1
4.  **Selecione os Funcionários:** Na tabela à direita, marque a caixa de seleção para um ou mais funcionários. Você pode usar a caixa no cabeçalho da tabela para selecionar todos de uma vez.    
5. **Envie a Solicitação:** Clique no botão "Enviar Solicitação". O sistema criará as pendências para todos os funcionários selecionados.
    
    
### 2.4. Revisando Documentos Enviados 
Quando um colaborador envia um documento, ele aparece na aba Revisão de Documentos.

1. Nesta tela, o RH verá a lista de documentos aguardando análise.
2. Para cada item, o RH pode:    
    - **Visualizar:** Clicar no nome do arquivo para abri-lo e verificar se está correto.
    - **Aprovar:** Se o documento estiver correto, o RH clica em "Aprovar". A pendência é encerrada e o documento é arquivado no perfil do funcionário.
    - **Reprovar:**  Se o documento estiver incorreto, o RH clica em "Reprovar". Uma janela se abrirá, exigindo o motivo da reprovação. A pendência retornará ao colaborador com esta observação para que ele possa corrigir e reenviar.

---

## 3. Fluxo para o Colaborador

### 3.1. Visualizando uma Solicitação

1.  Ao acessar a **Dashboard**, o colaborador verá um card chamado **"Documentos Solicitados"**.
2.  Este card listará todas as pendências de documentos, incluindo as que foram criadas automaticamente no seu primeiro acesso e as que o RH solicitou manualmente. Cada pendência terá o nome do documento solicitado.
3.  Caso um documento tenha sido **reprovado**, o motivo aparecerá em destaque logo abaixo da solicitação, instruindo o colaborador sobre o que precisa ser corrigido.

### 3.2. Enviando um Documento

1.  Na Dashboard, o colaborador clica no botão **"Enviar Documento"** ao lado da pendência desejada.
2.  Uma janela (modal) se abrirá, mostrando qual documento está sendo enviado.
3.  O colaborador clica em "Selecione o arquivo", escolhe o documento em seu computador e clica em **"Enviar"**.

Após o envio, a pendência desaparecerá da sua dashboard e o documento ficará aguardando a revisão do RH.