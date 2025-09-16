# Usar uma imagem oficial do Python como base
FROM python:3.11-slim

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo de dependências para o container
COPY requirements.txt .

# Instalar as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo o resto do código do projeto para o container
COPY . .

# Expor a porta que o Flask usa
EXPOSE 5000

# Comando para rodar a aplicação quando o container iniciar
# CMD ["flask", "run", "--host=0.0.0.0"]
#CMD ["flask", "run", "--host=0.0.0.0", "--debug"]
# SERVIDOR DE PRODUÇÃO:
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--worker-class", "gevent", "run:app"]
