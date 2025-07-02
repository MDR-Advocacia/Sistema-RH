import os
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis do .env

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
