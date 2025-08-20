# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app # type: ignore
from flask_login import login_user, logout_user, login_required, current_user # type: ignore
from flask_mail import Message
from . import mail
from .models import Usuario, Funcionario
from . import db


from ldap3.core.exceptions import LDAPBindError, LDAPException # LDAPException adicionado aqui
from flask import current_app
from ldap3 import Server, Connection, ALL
import uuid



auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')
    user = None

    if not username or not password:
        flash('Usuário e senha são obrigatórios.')
        return redirect(url_for('auth.login'))

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
        conn.unbind()

        # --- Lógica de Vinculação e Provisionamento CORRIGIDA ---
        user = Usuario.query.filter_by(email=ad_email).first()

        if not user:
            funcionario_existente = Funcionario.query.filter_by(nome=ad_full_name).first()
            
            if funcionario_existente:
                # Se o funcionário existe, verifica se ele JÁ TEM um usuário
                if funcionario_existente.usuario:
                    current_app.logger.info(f"Usuário AD '{ad_email}' corresponde a um funcionário com usuário já existente (ID: {funcionario_existente.usuario.id}). Usando usuário existente.")
                    user = funcionario_existente.usuario
                    # Garante que o e-mail esteja sincronizado
                    if user.email != ad_email:
                        user.email = ad_email
                        db.session.commit()
                else:
                    # Se o funcionário existe mas NÃO TEM usuário, cria e vincula um novo
                    current_app.logger.info(f"Vinculando usuário AD '{ad_email}' ao funcionário existente SEM usuário '{ad_full_name}' (ID: {funcionario_existente.id})")
                    user = Usuario(email=ad_email, funcionario_id=funcionario_existente.id, senha_provisoria=False)
                    user.set_password(uuid.uuid4().hex)
                    db.session.add(user)
                    db.session.commit()
            
            else:
                # NÃO ENCONTROU: Provisionamento de um novo funcionário
                current_app.logger.info(f"Provisionando novo funcionário e usuário para '{ad_email}' a partir do AD.")
                novo_funcionario = Funcionario(nome=ad_full_name, email=ad_email, cpf=f"AD_{ad_user.sAMAccountName.value}", cargo="A Definir", setor="A Definir")
                db.session.add(novo_funcionario)
                db.session.commit()
                user = Usuario(email=ad_email, funcionario_id=novo_funcionario.id, senha_provisoria=False)
                user.set_password(uuid.uuid4().hex)
                db.session.add(user)
                db.session.commit()
        
    except (LDAPBindError, LDAPException) as e:
        current_app.logger.warning(f"Falha na autenticação LDAP para '{username}': {e}. Tentando autenticação local.")
        user = None

    # --- TENTATIVA 2: Fallback para Autenticação Local ---
    if not user:
        user = Usuario.query.filter_by(email=username).first()
        if not user or not user.check_password(password):
            flash('Usuário ou senha inválidos.')
            return redirect(url_for('auth.login'))

    # --- Verificações Finais e Login ---
    if user.funcionario and user.funcionario.status == 'Suspenso':
        flash('Este usuário está suspenso e não pode acessar o sistema.', 'danger')
        return redirect(url_for('auth.login'))

    login_user(user)
    return redirect(url_for('main.index'))


@auth.route('/logout')
@login_required # Garante que apenas usuários logados podem deslogar
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao_senha')

        if not nova_senha or nova_senha != confirmacao:
            flash('As senhas não conferem ou estão em branco.')
            return redirect(url_for('auth.change_password'))

        # Atualiza a senha e a flag no banco
        current_user.set_password(nova_senha)
        current_user.senha_provisoria = False
        db.session.commit()

        flash('Senha alterada com sucesso! Você pode prosseguir.')
        return redirect(url_for('main.index'))

    return render_template('auth/change_password.html')

@auth.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Usuario.query.filter_by(email=email).first()
        if user:
            # Gerar token e enviar e-mail
            token = user.get_reset_password_token()
            msg = Message(
                'Redefinição de Senha - MDRH',
                sender=current_app.config['MAIL_SENDER'],
                recipients=[user.email]
            )
            msg.body = f'''Para redefinir sua senha, visite o seguinte link:
{url_for('auth.redefinir_senha', token=token, _external=True)}

Se você não solicitou esta alteração, ignore este e-mail.
'''
            mail.send(msg)
        
        flash('Se o e-mail estiver cadastrado em nosso sistema, um link de redefinição de senha foi enviado.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/esqueci_senha.html')


@auth.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    user = Usuario.verify_reset_password_token(token)
    if not user:
        flash('O link de redefinição de senha é inválido ou expirou.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao_senha')

        if not nova_senha or nova_senha != confirmacao:
            flash('As senhas não conferem ou estão em branco.', 'danger')
            return redirect(url_for('auth.redefinir_senha', token=token))

        user.set_password(nova_senha)
        user.senha_provisoria = False # Garante que a flag seja desativada
        db.session.commit()

        flash('Sua senha foi atualizada com sucesso! Você já pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/redefinir_senha.html')