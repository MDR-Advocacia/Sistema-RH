import os
from dotenv import load_dotenv

load_dotenv()  # carrega as variáveis do .env

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_SENDER = os.getenv('MAIL_SENDER')

    # Carregando token
    SECRET_KEY = os.getenv('SECRET_KEY')

    # Configurações do Active Directory
    LDAP_HOST = os.getenv('LDAP_HOST')
    LDAP_PORT = int(os.getenv('LDAP_PORT') or 389)
    LDAP_BASE_DN = os.getenv('LDAP_BASE_DN')
    LDAP_USER_OU = os.getenv('LDAP_USER_OU')
    LDAP_BIND_USER_DN = os.getenv('LDAP_BIND_USER_DN')
    LDAP_BIND_USER_PASSWORD = os.getenv('LDAP_BIND_USER_PASSWORD')
    AD_DEFAULT_PASSWORD = os.getenv('AD_DEFAULT_PASSWORD')

    # Pasta de arquivos 
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'uploads')
