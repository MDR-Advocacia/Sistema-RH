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
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Inicialização das extensões
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
scheduler = BackgroundScheduler()
login_manager.login_view = 'auth.login_get'
CORS_INSTANCE = CORS()

def format_datetime_local(utc_dt):
    if not utc_dt or not isinstance(utc_dt, datetime):
        return ""
    local_tz = pytz.timezone('America/Sao_Paulo') 
    if utc_dt.tzinfo is None:
        utc_dt = pytz.utc.localize(utc_dt)
    
    local_dt = utc_dt.astimezone(local_tz)
    return local_dt.strftime('%d/%m/%Y %H:%M:%S')

# --- NOVO FILTRO ADICIONADO ---
def nl2br(value):
    """Converte quebras de linha em tags <br>."""
    if not value:
        return ""
    return value.replace('\n', '<br>\n')

def create_app(config_name='default'):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    template_folder = os.path.join(project_root, 'templates')
    static_folder = os.path.join(project_root, 'static')
    
    app = Flask(__name__,
                template_folder=template_folder,
                static_folder=static_folder)
    
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    CORS_INSTANCE.init_app(app)
    login_manager.init_app(app)

    app.jinja_env.filters['format_datetime_local'] = format_datetime_local
    app.jinja_env.filters['localtime'] = format_datetime_local
    # REGISTRO DO NOVO FILTRO
    app.jinja_env.filters['nl2br'] = nl2br 

    from .models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    # --- Context Processor para injetar datetime e helpers ---
    @app.context_processor
    def inject_helpers():
        from datetime import datetime
        return dict(datetime=datetime)

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

    from .cadastros_gerais import cadastros_bp
    app.register_blueprint(cadastros_bp, url_prefix='/cadastros')

    from .vinculo_ad import vinculo_bp
    app.register_blueprint(vinculo_bp, url_prefix='/vinculo-ad')

    from .artigos import artigos as artigos_blueprint
    app.register_blueprint(artigos_blueprint)
    
    # --- ADIÇÕES DA FASE 1 (Helpdesk) ---
    from .chamados_web import chamados_web_bp
    app.register_blueprint(chamados_web_bp)
    from .chamados_api import chamados_api_bp
    app.register_blueprint(chamados_api_bp)
    
    # Tente importar o blueprint de ativos se ele existir, senão ignore
    try:
        from .ativos import ativos_bp
        app.register_blueprint(ativos_bp)
    except ImportError:
        pass
        
    # --- ADIÇÕES DA FASE 2 (Mural de Avisos) ---
    try:
        from .avisos import avisos_bp
        app.register_blueprint(avisos_bp)
    except ImportError:
        pass # Evita erro se o arquivo ainda não existir, mas ele deve existir agora
    # --- FIM DAS ADIÇÕES ---
    
    # --- SCHEDULER AUTOMÁTICO PARA O AD ---
    # Inicia o agendador apenas se não estiver em modo de debug/reloader
    # para evitar que o job rode duplicado.
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        try:
            from .ad_mirror import sync_ad_to_db_logic
            
            def job_sync_ad():
                with app.app_context():
                    print(">>> [AutoSync] Iniciando Sincronização Agendada do AD...")
                    try:
                        sync_ad_to_db_logic()
                        print(">>> [AutoSync] Sincronização Finalizada com Sucesso.")
                    except Exception as e:
                        print(f"!!! [AutoSync] Erro Crítico: {e}")

            # Agenda para rodar a cada 4 horas
            scheduler.add_job(func=job_sync_ad, trigger="interval", hours=4, id="sync_ad_job", replace_existing=True)
            
            if not scheduler.running:
                scheduler.start()
                print(">>> APScheduler Iniciado: Sync AD agendado a cada 4h.")
                
            atexit.register(lambda: scheduler.shutdown())
            
        except ImportError:
            print("Aviso: Não foi possível carregar o módulo de sincronização do AD.")
        except Exception as e:
            print(f"Erro ao configurar o scheduler: {e}")

    # --- Verificações Globais ---
    @app.before_request
    def check_user_status_before_request():
        if not current_user.is_authenticated or not request.endpoint or 'static' in request.endpoint or 'auth.' in request.endpoint:
            return

        if not current_user.funcionario:
            return

        if current_user.funcionario.status == 'Suspenso':
            from flask_login import logout_user
            logout_user()
            return redirect(url_for('auth.login_get'))
            
        # Verifica consentimento (se a lógica de consentimento estiver ativa no seu app)
        if hasattr(current_user, 'data_consentimento') and not current_user.data_consentimento:
             if request.endpoint not in ['main.consentimento', 'main.politica_privacidade', 'auth.logout']:
                 return redirect(url_for('main.consentimento'))

    @app.context_processor
    def inject_user_permissions():
        if current_user.is_authenticated:
            return dict(
                tem_permissao=current_user.tem_permissao,
                is_admin_ti=current_user.tem_permissao('admin_ti')
            )
        return dict(tem_permissao=lambda x: False, is_admin_ti=False)

    from manage import register_commands
    register_commands(app)

    return app