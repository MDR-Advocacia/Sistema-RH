import os
import uuid
from flask import current_app
from ldap3 import Server, Connection, ALL, Tls, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException
import ssl

def get_ad_connection():
    """Cria e retorna uma conexão autenticada com o AD usando a conta de serviço."""
    try:
        tls_config = Tls(validate=ssl.CERT_NONE)
        server = Server(
            current_app.config['LDAP_HOST'],
            port=int(current_app.config['LDAP_PORT']),
            get_info=ALL,
            use_ssl=True,
            tls=tls_config
        )
        conn = Connection(
            server,
            user=current_app.config['LDAP_BIND_USER_DN'],
            password=current_app.config['LDAP_BIND_USER_PASSWORD'],
            auto_bind=True
        )
        return conn
    except LDAPException as e:
        current_app.logger.error(f"Falha ao conectar ao AD com a conta de serviço: {e}")
        return None

def verificar_usuario_ad(username):
    """Verifica se um sAMAccountName já existe no AD."""
    conn = get_ad_connection()
    if not conn:
        return {'existe': False, 'error': 'Falha na conexão com o AD.'}
    
    try:
        search_filter = f'(sAMAccountName={username})'
        conn.search(
            search_base=current_app.config['LDAP_BASE_DN'],
            search_filter=search_filter,
            attributes=['displayName']
        )
        if conn.entries:
            display_name = conn.entries[0].displayName.value
            return {'existe': True, 'displayName': display_name}
        return {'existe': False}
    except LDAPException as e:
        current_app.logger.error(f"Erro ao verificar usuário no AD: {e}")
        return {'existe': False, 'error': str(e)}
    finally:
        if conn:
            conn.unbind()

# --- FUNÇÃO ATUALIZADA PARA O FLUXO COMPLETO ---
# app/ad_sync.py

def provisionar_usuario_ad(funcionario, username_manual=None, vincular=False):
    """
    Garante que um usuário exista no AD, com suporte para username manual e vinculação.
    """
    if vincular:
        # Se a intenção é apenas vincular, não precisamos conectar ao AD para criar.
        # Apenas retornamos os dados necessários para a vinculação no sistema.
        nome_parts = funcionario.nome.lower().split()
        primeiro_nome = nome_parts[0]
        sobrenome = nome_parts[-1] if len(nome_parts) > 1 else ''
        username = f"{primeiro_nome}.{sobrenome}" if sobrenome else primeiro_nome
        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        email_ad = f"{username}@{domain}"
        return True, "Vinculação manual solicitada.", email_ad

    conn = get_ad_connection()
    if not conn:
        return False, "Falha na conexão com o AD.", None

    try:
        # Define o username (padrão ou manual)
        if username_manual:
            username = username_manual.lower()
        else:
            nome_parts = funcionario.nome.lower().split()
            primeiro_nome = nome_parts[0]
            sobrenome = nome_parts[-1] if len(nome_parts) > 1 else ''
            username = f"{primeiro_nome}.{sobrenome}" if sobrenome else primeiro_nome
        
        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        user_principal_name = f"{username}@{domain}"
        user_dn = f"CN={funcionario.nome},{current_app.config['LDAP_USER_OU']}"

        # Verifica se o usuário já existe (a verificação primária é feita via API, esta é uma dupla checagem)
        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(sAMAccountName={username})', attributes=['cn'])

        if conn.entries:
            # Lógica de atualização para usuários existentes
            user_dn_existente = conn.entries[0].entry_dn
            modificacoes = {
                'displayName': [(MODIFY_REPLACE, [funcionario.nome])],
                'department': [(MODIFY_REPLACE, [funcionario.setor or 'N/A'])],
                'title': [(MODIFY_REPLACE, [funcionario.cargo or 'N/A'])],
            }
            conn.modify(user_dn_existente, modificacoes)
        else:
            # Fluxo de criação de novo usuário
            conn.add(
                user_dn,
                attributes={
                    'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
                    'cn': funcionario.nome,
                    'givenName': nome_parts[0].capitalize(),
                    'sn': ' '.join(nome_parts[1:]).title() if len(nome_parts) > 1 else nome_parts[0].capitalize(),
                    'displayName': funcionario.nome,
                    'userPrincipalName': user_principal_name,
                    'sAMAccountName': username,
                    'mail': funcionario.email
                }
            )
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao criar o objeto do usuÃ¡rio: {conn.result['description']} - {conn.result['message']}")

            senha_padrao = current_app.config.get('AD_DEFAULT_PASSWORD')
            if not senha_padrao:
                raise LDAPException("A senha padrÃ£o do AD (AD_DEFAULT_PASSWORD) nÃ£o estÃ¡ configurada no .env")

            quoted_password = '"' + senha_padrao + '"'
            encoded_password = quoted_password.encode('utf-16-le')

            conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_password])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao definir a senha (verifique a polÃ­tica de complexidade): {conn.result['description']} - {conn.result['message']}")
            
            conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, ['512'])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao ativar a conta: {conn.result['description']} - {conn.result['message']}")
            
            conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, [0])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao forÃ§ar troca de senha: {conn.result['description']} - {conn.result['message']}")

        return True, "UsuÃ¡rio provisionado no AD com sucesso.", user_principal_name

    except LDAPException as e:
        current_app.logger.error(f"Erro de LDAP ao provisionar/sincronizar usuÃ¡rio: {e}")
        return False, f"Erro de LDAP: {e}", None
    finally:
        if conn:
            conn.unbind()

# ALTERAR, DESABILITAR E REMOVER

def _alterar_status_usuario_ad(email, habilitar=True):
    conn = get_ad_connection()
    if not conn:
        return False, "Falha na conexão com o AD."

    try:
        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={email})', attributes=['userAccountControl'])
        if not conn.entries:
            return True, "Usuário não encontrado no AD, nenhuma ação necessária."

        user_dn = conn.entries[0].entry_dn
        novo_status = '512' if habilitar else '514'
        
        conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [novo_status])]})
        return True, f"Usuário {email} {'habilitado' if habilitar else 'desabilitado'} no AD."
    except LDAPException as e:
        current_app.logger.error(f"Erro ao alterar status do usuário {email} no AD: {e}")
        return False, "Erro ao alterar status no AD."
    finally:
        if conn:
            conn.unbind()

def habilitar_usuario_ad(email):
    return _alterar_status_usuario_ad(email, habilitar=True)

def desabilitar_usuario_ad(email):
    return _alterar_status_usuario_ad(email, habilitar=False)

def remover_usuario_ad(email):
    conn = get_ad_connection()
    if not conn:
        return False, "Falha na conexão com o AD."

    try:
        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={email})')
        if not conn.entries:
            return True, "Usuário não encontrado no AD, nenhuma ação necessária."

        user_dn = conn.entries[0].entry_dn
        conn.delete(user_dn)
        return True, f"Usuário {email} removido do AD com sucesso."
    except LDAPException as e:
        current_app.logger.error(f"Erro ao remover usuário {email} do AD: {e}")
        return False, "Erro ao remover usuário do AD."
    finally:
        if conn:
            conn.unbind()