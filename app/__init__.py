import os
from datetime import datetime
import pytz
from dotenv import load_dotenv # <-- Adicione esta linha

from flask import Flask, request, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail

from .config import Config

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv() # <-- Adicione esta linha

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
login_manager.login_view = 'auth.login'

def format_datetime_local(utc_dt):
    if not utc_dt or not isinstance(utc_dt, datetime):
        return ""
    local_tz = pytz.timezone('America/Sao_Paulo') 
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt.strftime('%d/%m/%Y %H:%M:%S')


def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    
    # --- CARREGAMENTO EXPLÍCITO DA SECRET_KEY ---
    # Carrega a configuração da classe Config E garante que a SECRET_KEY seja definida.
    app.config.from_object(Config)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

    if not app.config['SECRET_KEY']:
        raise ValueError("Nenhuma SECRET_KEY definida. Verifique seu arquivo .env")
    
    app.jinja_env.filters['localtime'] = format_datetime_local

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    CORS(app)
    login_manager.init_app(app)

    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # --- Blueprints ---
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

    # --- Verificações Globais ---
    @app.before_request
    def check_user_status_before_request():
        if not current_user.is_authenticated or not request.endpoint or 'static' in request.endpoint or 'auth.' in request.endpoint:
            return

        if current_user.senha_provisoria:
            if request.endpoint != 'auth.change_password':
                return redirect(url_for('auth.change_password'))
            return

        if not current_user.data_consentimento:
            if request.endpoint not in ['main.consentimento', 'main.politica_privacidade']:
                return redirect(url_for('main.consentimento'))

    return app