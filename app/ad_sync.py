from flask import current_app
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException

def get_ad_connection():
    """Cria e retorna uma conexão autenticada com o AD usando a conta de serviço."""
    try:
        server = Server(
            current_app.config['LDAP_HOST'],
            port=current_app.config['LDAP_PORT'],
            get_info=ALL
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

def provisionar_usuario_ad(funcionario):
    """
    Cria um usuário no AD em estado DESABILITADO. A ativação e definição
    de senha devem ser feitas manualmente pelo administrador de TI.
    """
    conn = get_ad_connection()
    if not conn:
        return False, "Falha na conexão com o AD.", None

    try:
        # ... (geração de username e UPN continua igual) ...
        nome_parts = funcionario.nome.lower().split()
        primeiro_nome = nome_parts[0]
        sobrenome = nome_parts[-1] if len(nome_parts) > 1 else ''
        username = f"{primeiro_nome}.{sobrenome}" if sobrenome else primeiro_nome
        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        user_principal_name = f"{username}@{domain}"
        user_dn = f"CN={funcionario.nome},{current_app.config['LDAP_USER_OU']}"

        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={user_principal_name})', attributes=['cn'])

        if conn.entries:
            # Se o usuário já existe, não fazemos nada para evitar erros.
            current_app.logger.info(f"Usuário {user_principal_name} já existe no AD. Nenhuma nova ação será tomada.")
            return True, "Usuário já existia no AD.", user_principal_name
        
        else:
            # --- FLUXO FINAL DE CRIAÇÃO ---
            current_app.logger.info(f"Provisionando usuário {user_principal_name} no AD em estado desabilitado.")
            
            # O valor 514 significa "Conta Normal, Desabilitada"
            # Esta é a única operação que faremos.
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
                    'mail': funcionario.email,
                    'userAccountControl': '514' # Flag para criar desabilitado
                }
            )
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao criar o objeto do usuário: {conn.result['description']} - {conn.result['message']}")

        return True, "Usuário criado DESABILITADO no AD. A TI precisa ativá-lo.", user_principal_name

    except LDAPException as e:
        current_app.logger.error(f"Erro de LDAP ao provisionar usuário: {e}")
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