# Manual de Operações e Recuperação de Desastres (Alpha)

Este documento descreve os procedimentos de backup, restauração e solução de problemas para o Sistema de RH.

## 1. Sistema de Backups Automatizados

O sistema foi configurado com um serviço de backup automatizado que roda em um container Docker separado (`backup`).

### Como Funciona:

- **Frequência:** O serviço de backup é programado para ser executado **uma vez a cada 24 horas**.
- **O Que é Salvo:** Ele cria uma cópia completa do banco de dados PostgreSQL, incluindo todos os funcionários, usuários, documentos, pontos e logs.
- **Formato:** O backup é salvo como um arquivo `.sql.gz` (um arquivo SQL comprimido).
- **Armazenamento:** Os backups são armazenados em um volume Docker persistente chamado `backups_data`. Isso garante que os arquivos de backup não sejam perdidos se os containers forem reiniciados.
- **Política de Retenção:** O script de backup automaticamente apaga backups com mais de **7 dias**, mantendo sempre os backups da última semana para economizar espaço.

### Em Caso de Erro:

Se o serviço de backup falhar, os logs podem ser consultados para diagnosticar o problema. Para ver os logs do serviço de backup em tempo real, use o comando:

`docker-compose logs -f backup`

Os erros mais comuns são relacionados a credenciais incorretas no arquivo `.env` (variáveis `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

## 2. Procedimentos Manuais de Backup e Acesso

Em alguns casos, pode ser necessário executar um backup manualmente ou baixar um arquivo de backup para o seu computador.

### 2.1. Executar um Backup Manualmente

Para forçar a execução da rotina de backup a qualquer momento:

`docker-compose run --rm backup`

*Este comando irá criar um novo container temporário, executar o script `backup.sh` e depois se autodestruir.*

### 2.2. Listar os Backups Disponíveis

Para ver todos os arquivos de backup que estão guardados no volume:

`docker-compose run --rm --entrypoint ls backup -l /backups`

*Este comando irá listar o conteúdo da pasta de backups. **Copie o nome do arquivo** que você deseja acessar.*

### 2.3. Baixar um Backup para o seu Computador

Para copiar um arquivo de backup específico do volume Docker para a sua máquina local:

1.  **Crie um container parado** para podermos acessar seus arquivos:
    `docker-compose run --name container_de_backup backup`
    *(Este comando roda o backup e deixa um container parado chamado `container_de_backup`)*

2.  **Copie o arquivo desejado:**
    `docker cp container_de_backup:/backups/NOME_DO_ARQUIVO.sql.gz .`
    *(Lembre-se de substituir o NOME_DO_ARQUIVO pelo nome real que você copiou. O `.` no final significa "para a pasta atual")*

3.  **(Opcional) Limpe o container parado:**
    `docker rm container_de_backup`

## 3. Procedimento de Restauração (Recuperação de Desastre)

Este procedimento deve ser usado em caso de perda total ou corrupção do banco de dados. Ele irá **substituir todos os dados atuais** pelos dados do arquivo de backup.

### Pré-requisitos:

-   O ambiente Docker deve estar de pé (`docker-compose up -d`).
-   Você deve ter o arquivo de backup (ex: `backup-2025-08-21.sql.gz`) na pasta raiz do seu projeto.
-   O banco de dados de destino (`mdrh_db`) deve existir, mas não precisa estar com as tabelas criadas.

### Passos para Restaurar:

1.  **Destrua o ambiente atual (se necessário):**
    Para garantir uma restauração limpa, é melhor começar com um banco de dados novo.
    `docker-compose down -v`
    `docker-compose up -d`
    *Atenção: O comando `down -v` apaga TODOS os dados atuais.*

2.  **Execute o Comando de Restauração:**
    Este comando descomprime o arquivo de backup e envia seu conteúdo diretamente para o cliente `psql` dentro do container do banco de dados.
    `gunzip < NOME_DO_SEU_BACKUP.sql.gz | docker-compose exec -T db psql -U mdrh_user -d mdrh_db`
    *Substitua `NOME_DO_SEU_BACKUP.sql.gz` pelo nome do seu arquivo.*
    *`-T` desabilita a alocação de um pseudo-TTY, o que é necessário para redirecionar o `stdin`.*
    *(No Windows, é recomendado usar o terminal do WSL ou Git Bash para este comando)*

3.  **Sincronize os Contadores de ID:**
    Após a restauração, os contadores de ID do PostgreSQL precisam ser atualizados para o valor mais alto de cada tabela para evitar erros de "chave duplicada".
    `docker-compose exec db psql -U mdrh_user -d mdrh_db -c "SELECT setval('funcionario_id_seq', (SELECT MAX(id) FROM funcionario));"`
    `docker-compose exec db psql -U mdrh_user -d mdrh_db -c "SELECT setval('usuario_id_seq', (SELECT MAX(id) FROM usuario));"`
    *Adicione comandos semelhantes para outras tabelas com IDs sequenciais se necessário.*

Após estes passos, seu banco de dados estará completamente restaurado ao estado em que se encontrava no momento em que o backup foi feito.