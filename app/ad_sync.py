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

# --- FUNÇÃO ATUALIZADA PARA O FLUXO COMPLETO ---
def provisionar_usuario_ad(funcionario):
    """
    Garante que um usuário exista no AD, define uma senha padrão, o ativa e
    força a alteração da senha no primeiro login.
    """
    conn = get_ad_connection()
    if not conn:
        return False, "Falha na conexão com o AD.", None

    try:
        nome_parts = funcionario.nome.lower().split()
        primeiro_nome = nome_parts[0]
        sobrenome = nome_parts[-1] if len(nome_parts) > 1 else ''
        username = f"{primeiro_nome}.{sobrenome}" if sobrenome else primeiro_nome
        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        user_principal_name = f"{username}@{domain}"
        user_dn = f"CN={funcionario.nome},{current_app.config['LDAP_USER_OU']}"

        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={user_principal_name})', attributes=['cn'])

        if conn.entries:
            # Lógica de atualização para usuários existentes (não mexe na senha)
            current_app.logger.info(f"Usuário {user_principal_name} já existe no AD. Sincronizando dados.")
            user_dn_existente = conn.entries[0].entry_dn
            modificacoes = {
                'displayName': [(MODIFY_REPLACE, [funcionario.nome])],
                'department': [(MODIFY_REPLACE, [funcionario.setor or 'N/A'])],
                'title': [(MODIFY_REPLACE, [funcionario.cargo or 'N/A'])],
            }
            conn.modify(user_dn_existente, modificacoes)
        else:
            # Fluxo de criação de novo usuário
            current_app.logger.info(f"Provisionando usuário {user_principal_name} no AD.")
            
            conn.add(
                user_dn,
                attributes={
                    'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
                    'cn': funcionario.nome,
                    'givenName': primeiro_nome.capitalize(),
                    'sn': ' '.join(nome_parts[1:]).title(),
                    'displayName': funcionario.nome,
                    'userPrincipalName': user_principal_name,
                    'sAMAccountName': username,
                    'mail': funcionario.email
                }
            )
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao criar o objeto do usuário: {conn.result['description']} - {conn.result['message']}")

            # --- INÍCIO DA ALTERAÇÃO: MÉTODO DIRETO PARA DEFINIR SENHA ---
            senha_padrao = current_app.config.get('AD_DEFAULT_PASSWORD')
            if not senha_padrao:
                raise LDAPException("A senha padrão do AD (AD_DEFAULT_PASSWORD) não está configurada no .env")

            # Formata a senha para o atributo unicodePwd do AD
            quoted_password = '"' + senha_padrao + '"'
            encoded_password = quoted_password.encode('utf-16-le')

            # Usa o método de modificação padrão para definir a senha
            conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_password])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao definir a senha (verifique a política de complexidade): {conn.result['description']} - {conn.result['message']}")
            # --- FIM DA ALTERAÇÃO ---
            
            conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, ['512'])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao ativar a conta: {conn.result['description']} - {conn.result['message']}")
            
            conn.modify(user_dn, {'pwdLastSet': [(MODIFY_REPLACE, [0])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao forçar troca de senha: {conn.result['description']} - {conn.result['message']}")

        return True, "Usuário provisionado no AD com sucesso.", user_principal_name

    except LDAPException as e:
        current_app.logger.error(f"Erro de LDAP ao provisionar/sincronizar usuário: {e}")
        return False, f"Erro de LDAP: {e}", None
    finally:
        if conn:
            conn.unbind()

# (As outras funções de habilitar, desabilitar e remover continuam aqui)

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