import os
from dotenv import load_dotenv

# Define o caminho base do projeto para encontrar o arquivo .env
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    """Configuração base que todas as outras herdarão."""
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(basedir, '..', 'uploads')
    
    # Configurações de E-mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SENDER = os.environ.get('MAIL_SENDER')

    # Carregando token
    SECRET_KEY = os.getenv('SECRET_KEY')

    # Configurações do Active Directory
    LDAP_HOST = os.environ.get('LDAP_HOST')
    LDAP_PORT = os.environ.get('LDAP_PORT')
    LDAP_BASE_DN = os.environ.get('LDAP_BASE_DN')
    LDAP_USERS_DN = os.environ.get('LDAP_USERS_DN')
    LDAP_BIND_USER_DN = os.environ.get('LDAP_BIND_USER_DN')
    LDAP_BIND_USER_PASSWORD = os.environ.get('LDAP_BIND_USER_PASSWORD')
    AD_DEFAULT_PASSWORD = os.environ.get('AD_DEFAULT_PASSWORD')

    # Pasta de arquivos 
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__name__)), 'uploads')

class DevelopmentConfig(Config):
    """Configuração para o ambiente de desenvolvimento."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')

class TestingConfig(Config):
    """Configuração para o ambiente de testes."""
    TESTING = True
    # Usa um banco de dados SQLite em memória para os testes serem rápidos e isolados
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' 
    WTF_CSRF_ENABLED = False # Desabilita tokens CSRF nos testes de formulário

# Dicionário para acessar as classes de configuração pelo nome
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}    
