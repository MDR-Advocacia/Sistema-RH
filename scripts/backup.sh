#!/bin/bash

set -o pipefail

FILENAME="backup-$(date +%Y-%m-%d_%H-%M-%S).sql.gz"
BACKUP_DIR="/backups"

mkdir -p ${BACKUP_DIR}

echo "Iniciando backup do banco de dados ${POSTGRES_DB}..."

# Adicionamos o nome do banco de dados ($POSTGRES_DB) ao final do comando
pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "${BACKUP_DIR}/${FILENAME}"

if [ $? -eq 0 ]; then
  echo "Backup [${FILENAME}] criado com sucesso."
else
  echo "ERRO: Falha ao criar o backup."
  exit 1
fi

echo "Limpando backups com mais de 7 dias..."
find ${BACKUP_DIR} -type f -name "*.sql.gz" -mtime +7 -delete
echo "Limpeza concluída."