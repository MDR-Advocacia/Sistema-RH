# app/__init__.py

import os
from datetime import datetime
import pytz
from flask import Flask, request, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from .config import config

# Inicialização das extensões
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'
CORS_INSTANCE = CORS()

def format_datetime_local(utc_dt):
    if not utc_dt or not isinstance(utc_dt, datetime):
        return ""
    local_tz = pytz.timezone('America/Sao_Paulo') 
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt.strftime('%d/%m/%Y %H:%M:%S')

def create_app(config_name='default'):
    # --- AQUI ESTÁ A CORREÇÃO ---
    # Constrói caminhos absolutos para as pastas, tornando a localização robusta
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_folder = os.path.join(project_root, 'templates')
    static_folder = os.path.join(project_root, 'static')
    
    app = Flask(__name__,
                template_folder=template_folder,
                static_folder=static_folder)
    
    # Carrega a configuração correta (development, testing, etc.)
    app.config.from_object(config[config_name])

    # Associa as extensões à instância do app
    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    CORS_INSTANCE.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.filters['localtime'] = format_datetime_local

    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        # AVISO DE LEGADO: A forma moderna é db.session.get(Usuario, int(user_id))
        return db.session.get(Usuario, int(user_id))

    # --- Registro dos Blueprints ---
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from .documentos import documentos_bp
    app.register_blueprint(documentos_bp, url_prefix='/documentos')
    
    from .perfil import perfil_bp
    app.register_blueprint(perfil_bp, url_prefix='/perfil')
    
    from .ponto import ponto_bp
    app.register_blueprint(ponto_bp, url_prefix='/ponto')
    
    from .denuncias import denuncias_bp
    app.register_blueprint(denuncias_bp, url_prefix='/denuncias')

    # --- Verificações Globais ---
    @app.before_request
    def check_user_status_before_request():
        # Ignora a verificação para endpoints não autenticados ou de arquivos estáticos
        if not current_user.is_authenticated or not request.endpoint or 'static' in request.endpoint or 'auth.' in request.endpoint:
            return

        # Redireciona para a página de consentimento se ainda não foi dado
        if not current_user.data_consentimento:
            if request.endpoint not in ['main.consentimento', 'main.politica_privacidade']:
                return redirect(url_for('main.consentimento'))

    # --- REGISTRO DOS COMANDOS CLI ---
    from manage import register_commands
    register_commands(app)

    return app