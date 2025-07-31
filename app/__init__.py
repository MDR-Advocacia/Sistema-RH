from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from .config import Config
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

import os
print("DB URI:", os.getenv('DATABASE_URL'))

def create_app():
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(Config)
    # Adicione uma SECRET_KEY, essencial para a segurança da sessão
    app.config['SECRET_KEY'] = 'uma-chave-secreta-muito-segura-trocar-depois'

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    # Inicialize o LoginManager com a aplicação
    login_manager.init_app(app)

    # Importe os modelos aqui para que o user_loader os encontre
    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        # Esta função é usada pelo Flask-Login para recarregar o objeto do usuário
        # a partir do ID do usuário armazenado na sessão.
        return Usuario.query.get(int(user_id))

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # --- NOVO: Vamos registrar o blueprint de autenticação ---
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    # --- Registra o blueprint de documentos ---
    from .documentos import documentos_bp
    app.register_blueprint(documentos_bp, url_prefix='/documentos')


    return app