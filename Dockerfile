# Usa uma imagem leve do Python 3.11
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para o PostgreSQL (libpq) e compilação
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia o requirements.txt primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt
# Instala o Gunicorn para rodar o servidor de produção
RUN pip install gunicorn

# Copia todo o restante do código para dentro do container
COPY . .

# Cria a pasta de uploads se não existir (para evitar erros de permissão)
RUN mkdir -p uploads

# Expõe a porta 5000
EXPOSE 5000

# Comando para iniciar o servidor (Usando Gunicorn para performance)
# "run:app" significa: arquivo run.py, objeto app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]