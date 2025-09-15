#!/bin/bash
set -e

# O diretório para salvar os backups dentro do contêiner,
# que está mapeado para a sua pasta local 'backups'
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"_%d-%m-%Y_%H-%M-%S")
FILE_NAME="backup-${TIMESTAMP}.sql"
FILE_PATH="${BACKUP_DIR}/${FILE_NAME}"

echo "Iniciando o backup do banco de dados '${POSTGRES_DB}'..."

# Garante que o diretório de backups exista
mkdir -p ${BACKUP_DIR}

# --- COMANDO PRINCIPAL CORRIGIDO ---
# Removemos o 'docker-compose exec'. O pg_dump é executado diretamente
# dentro do contêiner 'backup' e se conecta ao 'db' através da rede do Docker.
pg_dump -h "${PGHOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -F c -b -v -f "${FILE_PATH}"

echo "Backup concluído com sucesso: ${FILE_PATH}"

# Limpa backups antigos (mantém os 7 mais recentes)
echo "Limpando backups antigos..."
ls -tp ${BACKUP_DIR}/backup-*.sql | tail -n +8 | xargs -I {} rm -- {}
echo "Limpeza concluída."