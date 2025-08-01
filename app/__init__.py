import os
from datetime import datetime
import pytz

from flask import Flask, request, redirect, url_for
from flask_cors import CORS
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

# --- Filtro de Fuso Horário ---
def format_datetime_local(utc_dt):
    """Filtro Jinja para converter um datetime UTC para o fuso -03:00."""
    if not utc_dt or not isinstance(utc_dt, datetime):
        return ""
    local_tz = pytz.timezone('America/Sao_Paulo') # Representação padrão para -03:00
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt.strftime('%d/%m/%Y %H:%M:%S')


def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(Config)
    app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura-trocar-depois'
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, '..', 'uploads')
    
    # Registra o filtro Jinja
    app.jinja_env.filters['localtime'] = format_datetime_local

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    login_manager.init_app(app)

    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # --- Registro dos Blueprints ---
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .documentos import documentos_bp
    app.register_blueprint(documentos_bp, url_prefix='/documentos')

    from .perfil import perfil_bp
    app.register_blueprint(perfil_bp, url_prefix='/perfil')

    # --- Verificação de Senha Provisória ---
    @app.before_request
    def check_for_temporary_password():
        # A condição agora verifica se 'request.endpoint' existe antes de usá-lo
        if (current_user.is_authenticated and 
            request.endpoint and 
            'auth.' not in request.endpoint and 
            'static' not in request.endpoint):
            
            if current_user.senha_provisoria and request.endpoint != 'perfil.editar_perfil':
                return redirect(url_for('auth.change_password'))

    return app