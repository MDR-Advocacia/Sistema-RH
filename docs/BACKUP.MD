## COMO FAZER BACKUP EM DOIS PASSOS:

- faço o backup: ```docker-compose run --rm backup```

- passo o arquivo de backup pra ele subir: ```docker-compose run --rm restore backups/ARQUIVO-DE-BACKUP.sql```