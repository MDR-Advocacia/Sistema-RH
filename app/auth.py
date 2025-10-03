# app/auth.py

from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app # type: ignore
from flask_login import login_user, logout_user, login_required, current_user # type: ignore
from flask_mail import Message
from sqlalchemy import func # <-- ADICIONADO: Import necessário para a correção
from . import mail
from app.models import TipoDocumento, RequisicaoDocumento, Funcionario, Usuario 
from . import db


from ldap3.core.exceptions import LDAPBindError, LDAPException # LDAPException adicionado aqui
from flask import current_app
from ldap3 import Server, Connection, ALL
import uuid



auth = Blueprint('auth', __name__)

# --- CORREÇÃO 1: Renomeando a função para evitar conflitos ---
@auth.route('/login', methods=['GET'])
def login_get():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = None

    if not username or not password:
        flash('Usuário e senha são obrigatórios.')
        # --- CORREÇÃO 2: Apontando para a nova função ---
        return redirect(url_for('auth.login_get'))

    # --- TENTATIVA 1: Autenticação via Active Directory ---
    try:
        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        user_for_bind = f'{username}@{domain}'

        server = Server(current_app.config['LDAP_HOST'], get_info=ALL)
        conn = Connection(server, user=user_for_bind, password=password, auto_bind=True)
        
        conn.search(
            search_base=current_app.config['LDAP_BASE_DN'],
            search_filter=f'(&(objectClass=person)(sAMAccountName={username}))',
            attributes=['cn', 'mail', 'sAMAccountName']
        )

        if not conn.entries:
            conn.unbind()
            raise LDAPException(f"Usuário {username} autenticado, mas não foi possível buscar seus dados no AD.")

        ad_user = conn.entries[0]
        ad_full_name = ad_user.cn.value
        ad_email = ad_user.mail.value if ad_user.mail else f"{username}@{domain}"
        ad_username = ad_user.sAMAccountName.value
        conn.unbind()

        # --- Lógica de Vinculação e Provisionamento CORRIGIDA ---
        user = Usuario.query.filter(func.lower(Usuario.username) == func.lower(ad_username)).first()

        if user:
            # Usuário encontrado! Apenas garantimos que o email e o nome do funcionário estão sincronizados.
            current_app.logger.info(f"Usuário '{ad_username}' encontrado no DB local (ID: {user.id}).")
            if user.email.lower() != ad_email.lower():
                user.email = ad_email
            if user.funcionario and user.funcionario.nome.lower() != ad_full_name.lower():
                user.funcionario.nome = ad_full_name
        else:
            # Usuário não encontrado pelo username. Agora vamos tentar vincular ou criar.
            current_app.logger.info(f"Usuário '{ad_username}' não encontrado. Tentando vincular ou provisionar.")
            
            # Tenta encontrar um funcionário com nome correspondente que AINDA NÃO TENHA um usuário
            funcionario_sem_usuario = Funcionario.query.filter(
                func.lower(Funcionario.nome) == func.lower(ad_full_name),
                Funcionario.usuario == None
            ).first()

            if funcionario_sem_usuario:
                # Encontramos um funcionário correspondente sem usuário. Vamos criar e vincular.
                current_app.logger.info(f"Vinculando usuário AD '{ad_username}' ao funcionário existente '{ad_full_name}' (ID: {funcionario_sem_usuario.id})")
                user = Usuario(
                    email=ad_email, 
                    username=ad_username,
                    funcionario_id=funcionario_sem_usuario.id
                )
                user.set_password(uuid.uuid4().hex) # Define senha aleatória, pois a auth é via AD
                db.session.add(user)
            else:
                # Se não encontramos um funcionário para vincular, criamos um novo funcionário e usuário.
                current_app.logger.info(f"Provisionando novo funcionário e usuário para '{ad_username}' a partir do AD.")
                
                cpf_ficticio = f"AD_{ad_username}"
                if Funcionario.query.filter_by(cpf=cpf_ficticio).first():
                    raise LDAPException(f"Erro de provisionamento: funcionário com CPF fictício '{cpf_ficticio}' já existe.")

                novo_funcionario = Funcionario(nome=ad_full_name, email=ad_email, cpf=cpf_ficticio)
                db.session.add(novo_funcionario)
                db.session.flush() # Para obter o ID do novo funcionário

                user = Usuario(
                    email=ad_email, 
                    username=ad_username,
                    funcionario_id=novo_funcionario.id
                )
                user.set_password(uuid.uuid4().hex)
                db.session.add(user)
        
    except (LDAPBindError, LDAPException) as e:
        current_app.logger.warning(f"Falha na autenticação LDAP para '{username}': {e}. Tentando autenticação local.")
        user = None

    # --- TENTATIVA 2: Fallback para Autenticação Local ---
    if not user:
        # Busca pelo username (que pode ser email para contas antigas)
        user = Usuario.query.filter(func.lower(Usuario.username) == func.lower(username)).first()
        if not user or not user.check_password(password):
            flash('Usuário ou senha inválidos.')
            # --- CORREÇÃO 2: Apontando para a nova função ---
            return redirect(url_for('auth.login_get'))

    # --- Verificações Finais e Login ---
    if user.funcionario and user.funcionario.status == 'Suspenso':
        flash('Este usuário está suspenso e não pode acessar o sistema.', 'danger')
        # --- CORREÇÃO 2: Apontando para a nova função ---
        return redirect(url_for('auth.login_get'))
    
    # Processo de primeiro login para gerar pendências
    if not user.primeiro_login_completo and user.funcionario:
        tipos_obrigatorios = TipoDocumento.query.filter_by(obrigatorio_na_admissao=True).all()
        if tipos_obrigatorios:
            for tipo in tipos_obrigatorios:
                existe = RequisicaoDocumento.query.filter_by(
                    destinatario_id=user.funcionario.id, tipo_documento_id=tipo.id
                ).first()
                if not existe:
                    db.session.add(RequisicaoDocumento(destinatario_id=user.funcionario.id, tipo_documento_id=tipo.id, status='Pendente'))
            flash('Detectamos que este é seu primeiro acesso! Verifique suas pendências de documentos de admissão.', 'info')
        user.primeiro_login_completo = True

    # Atualiza a data do último login
    user.ultimo_login_em = datetime.now(timezone.utc)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro no commit final do login para {user.username}: {e}")
        flash('Ocorreu um erro ao finalizar o processo de login. Contate o suporte.', 'danger')
        return redirect(url_for('auth.login_get'))

    login_user(user)
    return redirect(url_for('main.index'))


@auth.route('/logout')
@login_required # Garante que apenas usuários logados podem deslogar
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['POST'])
@login_required
def change_password_post():
    nova_senha = request.form.get('nova_senha')
    confirmacao = request.form.get('confirmacao_senha')
    consentimento = request.form.get('consentimento') # Pega o valor do checkbox

    if not nova_senha or nova_senha != confirmacao:
        flash('As senhas não conferem ou estão em branco.', 'danger')
        return redirect(url_for('auth.change_password'))

    # Validação do consentimento
    if not consentimento:
        flash('Você precisa concordar com os termos de uso para continuar.', 'danger')
        return redirect(url_for('auth.change_password'))

    # Salva a nova senha e a data do consentimento
    current_user.set_password(nova_senha)
    current_user.senha_provisoria = False
    current_user.data_consentimento = datetime.utcnow()
    db.session.commit()

    flash('Senha atualizada com sucesso! Bem-vindo(a) ao sistema.', 'success')
    return redirect(url_for('main.index'))