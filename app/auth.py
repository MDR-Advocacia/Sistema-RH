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
            # CORREÇÃO: Utilizando func.lower() para busca case-insensitive
            funcionario_existente = Funcionario.query.filter(func.lower(Funcionario.nome) == func.lower(ad_full_name)).first()
            
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
    
    # 1. Verificamos se o processo de primeiro login já foi concluído
    if not user.primeiro_login_completo:
        
        # 2. Usamos o relacionamento direto para obter o funcionário.
        funcionario = user.funcionario
        
        if funcionario:
            # Buscamos todos os tipos de documento que são obrigatórios na admissão
            tipos_obrigatorios = TipoDocumento.query.filter_by(obrigatorio_na_admissao=True).all()
            
            if tipos_obrigatorios:
                for tipo in tipos_obrigatorios:
                    # Verificamos se já não existe uma pendência idêntica
                    existe = RequisicaoDocumento.query.filter_by(
                        destinatario_id=funcionario.id,
                        tipo_documento_id=tipo.id
                    ).first()

                    if not existe:
                        nova_requisicao = RequisicaoDocumento(
                            destinatario_id=funcionario.id,
                            tipo_documento_id=tipo.id,
                            status='Pendente'
                        )
                        db.session.add(nova_requisicao)
                
                flash('Detectamos que este é seu primeiro acesso! Verifique suas pendências de documentos de admissão.', 'info')

        # 3. Marcamos que o processo foi concluído para não rodar novamente
        user.primeiro_login_completo = True

    # 4. Atualizamos a data do último login em TODOS os acessos
    user.ultimo_login_em = datetime.now(timezone.utc)
    
    # 5. Commitamos as alterações (novo status, data e requisições)
    #    Este commit é importante que ocorra ANTES do login_user
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao criar requisições/atualizar login para {user.username}: {e}")
        # A falha aqui não deve impedir o login, mas registramos o erro e avisamos.
        flash('Ocorreu um erro ao gerar suas pendências de documentos. Por favor, contate o RH.', 'danger')


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