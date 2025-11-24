# app/auth.py

from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app # type: ignore
from flask_login import login_user, logout_user, login_required, current_user # type: ignore
from flask_mail import Message
from sqlalchemy import func
from . import mail
# IMPORTAÇÕES ATUALIZADAS (Permissao e Setor)
from app.models import TipoDocumento, RequisicaoDocumento, Funcionario, Usuario, Permissao, Setor
from . import db


from ldap3.core.exceptions import LDAPBindError, LDAPException
from flask import current_app
from ldap3 import Server, Connection, ALL
import uuid

# --- O MAPA DE GRUPOS FOI REMOVIDO POIS A LÓGICA AGORA É COMPOSTA ---

auth = Blueprint('auth', __name__)

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
            attributes=['cn', 'mail', 'sAMAccountName', 'memberOf', 'department']
        )

        if not conn.entries:
            conn.unbind()
            raise LDAPException(f"Usuário {username} autenticado, mas não foi possível buscar seus dados no AD.")

        ad_user = conn.entries[0]
        ad_full_name = ad_user.cn.value
        ad_email = ad_user.mail.value if ad_user.mail else f"{username}@{domain}"
        ad_username = ad_user.sAMAccountName.value
        ad_grupos_dns = ad_user.memberOf.values if ad_user.memberOf else []
        ad_departamento_str = ad_user.department.value if ad_user.department else None
        
        conn.unbind()

        # --- LÓGICA DE GRUPOS (AÇÃO 0.1 ATUALIZADA) ---
        # Extrai apenas o NOME do grupo do "Distinguished Name" (DN)
        # Ex: "CN=TI,CN=Users,DC=mdr,DC=local" -> "TI"
        ad_group_names = {dn.split(',')[0].split('=')[1] for dn in ad_grupos_dns}
        # -----------------------------------------------

        user = Usuario.query.filter(func.lower(Usuario.username) == func.lower(ad_username)).first()

        if user:
            # Usuário encontrado! Sincroniza e corrige os dados.
            current_app.logger.info(f"Usuário '{ad_username}' encontrado no DB local (ID: {user.id}).")
            
            if user.funcionario and user.email != user.funcionario.email:
                user.email = user.funcionario.email

            # --- INÍCIO DA NOVA LÓGICA DE PERMISSÃO COMPOSTA ---
            
            # 1. Busca todas as permissões do banco UMA SÓ VEZ.
            permissoes_db = {p.nome: p for p in Permissao.query.all()}
            
            # 2. Lista onde vamos adicionar as permissões que o usuário DEVE TER.
            permissoes_para_adicionar = []

            # 3. Lógica de Mapeamento Base
            if 'TI' in ad_group_names and 'tecnico_ti' in permissoes_db:
                permissoes_para_adicionar.append(permissoes_db['tecnico_ti'])
            
            if 'Supervisores' in ad_group_names and 'supervisor' in permissoes_db:
                permissoes_para_adicionar.append(permissoes_db['supervisor'])
            
            # 4. Lógica "RH engloba DP" (Sua regra)
            # Se for do RH OU do DP, ganha a permissão de DP.
            if ('Recursos Humanos' in ad_group_names or 'Departamento Pessoal' in ad_group_names) and 'dp_pessoal' in permissoes_db:
                permissoes_para_adicionar.append(permissoes_db['dp_pessoal'])

            # 5. Lógica Composta "Admin RH" (Sua regra)
            # admin_rh = Recursos Humanos E Supervisores
            if 'Recursos Humanos' in ad_group_names and 'Supervisores' in ad_group_names and 'admin_rh' in permissoes_db:
                permissoes_para_adicionar.append(permissoes_db['admin_rh'])

            # 6. Lógica Composta "Admin TI" (Sua regra)
            # supervisor_ti = TI E Supervisores
            if 'TI' in ad_group_names and 'Supervisores' in ad_group_names and 'supervisor_ti' in permissoes_db:
                permissoes_para_adicionar.append(permissoes_db['supervisor_ti'])

            # 7. Limpa permissões antigas e aplica as novas (sem duplicatas)
            user.permissoes.clear()
            user.permissoes.extend(list(set(permissoes_para_adicionar)))
            
            # --- FIM DA NOVA LÓGICA DE PERMISSÃO ---

            # --- INÍCIO DA SINCRONIZAÇÃO DE SETOR (AÇÃO 0.2 - Mantida) ---
            if user.funcionario and ad_departamento_str:
                setor_db = Setor.query.filter(func.lower(Setor.nome) == func.lower(ad_departamento_str)).first()
                if setor_db:
                    user.funcionario.setor_id = setor_db.id
                else:
                    current_app.logger.warning(f"Sincronização AD: Setor '{ad_departamento_str}' não encontrado. Criando novo setor no banco...")
                    novo_setor = Setor(nome=ad_departamento_str)
                    db.session.add(novo_setor)
                    db.session.flush()
                    user.funcionario.setor_id = novo_setor.id
            # --- FIM DA SINCRONIZAÇÃO DE SETOR ---
            
        else:
            # Usuário não encontrado, tenta vincular ou criar.
            current_app.logger.info(f"Usuário '{ad_username}' não encontrado. Tentando vincular ou provisionar.")
            
            funcionario_sem_usuario = Funcionario.query.filter(
                func.lower(Funcionario.nome) == func.lower(ad_full_name),
                Funcionario.usuario == None
            ).first()

            if funcionario_sem_usuario:
                current_app.logger.info(f"Vinculando usuário AD '{ad_username}' ao funcionário existente '{ad_full_name}' (ID: {funcionario_sem_usuario.id})")
                email_para_usuario = funcionario_sem_usuario.email if funcionario_sem_usuario.email else ad_email
                
                user = Usuario(
                    email=email_para_usuario, 
                    username=ad_username,
                    funcionario_id=funcionario_sem_usuario.id
                )
                user.set_password(uuid.uuid4().hex)
                db.session.add(user)
            else:
                current_app.logger.info(f"Provisionando novo funcionário e usuário para '{ad_username}' a partir do AD.")
                
                cpf_ficticio = f"AD_{ad_username}"
                if Funcionario.query.filter_by(cpf=cpf_ficticio).first():
                    raise LDAPException(f"Erro de provisionamento: funcionário com CPF fictício '{cpf_ficticio}' já existe.")

                novo_funcionario = Funcionario(nome=ad_full_name, email=ad_email, cpf=cpf_ficticio)
                db.session.add(novo_funcionario)
                db.session.flush()

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
        user = Usuario.query.filter(func.lower(Usuario.username) == func.lower(username)).first()
        if not user or not user.check_password(password):
            flash('Usuário ou senha inválidos.')
            return redirect(url_for('auth.login_get'))

    # --- Verificações Finais e Login ---
    if user.funcionario and user.funcionario.status == 'Suspenso':
        flash('Este usuário está suspenso e não pode acessar o sistema.', 'danger')
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
@login_required 
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['POST'])
@login_required
def change_password_post():
    nova_senha = request.form.get('nova_senha')
    confirmacao = request.form.get('confirmacao_senha')
    consentimento = request.form.get('consentimento') 

    if not nova_senha or nova_senha != confirmacao:
        flash('As senhas não conferem ou estão em branco.', 'danger')
        return redirect(url_for('auth.change_password'))

    if not consentimento:
        flash('Você precisa concordar com os termos de uso para continuar.', 'danger')
        return redirect(url_for('auth.change_password'))

    current_user.set_password(nova_senha)
    current_user.senha_provisoria = False
    current_user.data_consentimento = datetime.utcnow()
    db.session.commit()

    flash('Senha atualizada com sucesso! Bem-vindo(a) ao sistema.', 'success')
    return redirect(url_for('main.index'))