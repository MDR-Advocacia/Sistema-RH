from flask import current_app
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE
from ldap3.core.exceptions import LDAPException

def get_ad_connection():
    # ... (esta função continua igual)
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

def provisionar_usuario_ad(funcionario, senha_inicial=None):
    """
    Garante que um usuário exista no AD e esteja com os dados sincronizados.
    Se a senha_inicial for fornecida, cria um novo usuário.
    Se não, apenas atualiza um usuário existente.
    """
    conn = get_ad_connection()
    if not conn:
        return False, "Não foi possível conectar ao servidor do Active Directory."

    try:
        # Padroniza o username e o email (UPN)
        nome_parts = funcionario.nome.lower().split()
        primeiro_nome = nome_parts[0]
        sobrenome = nome_parts[-1] if len(nome_parts) > 1 else ''
        username = f"{primeiro_nome}.{sobrenome}" if sobrenome else primeiro_nome
        
        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        user_principal_name = f"{username}@{domain}"
        
        # O e-mail do funcionário no nosso sistema DEVE ser o UPN do AD
        funcionario.email = user_principal_name
        
        user_dn = f"CN={funcionario.nome},{current_app.config['LDAP_USER_OU']}"

        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={user_principal_name})', attributes=['cn'])

        if conn.entries:
            # --- USUÁRIO EXISTE: ATUALIZAR ---
            current_app.logger.info(f"Usuário {user_principal_name} já existe no AD. Sincronizando alterações.")
            user_dn_existente = conn.entries[0].entry_dn
            
            # Prepara um dicionário com os campos a serem atualizados
            modificacoes = {
                'department': [(MODIFY_REPLACE, [funcionario.setor or 'N/A'])],
                'title': [(MODIFY_REPLACE, [funcionario.cargo or 'N/A'])],
                # Adicione outros campos que queira sincronizar aqui
            }
            conn.modify(user_dn_existente, modificacoes)
            
        elif senha_inicial:
            # --- USUÁRIO NÃO EXISTE E SENHA FOI FORNECIDA: CRIAR ---
            current_app.logger.info(f"Provisionando usuário {user_principal_name} no AD.")
            
            # Passo A: Cria o objeto do usuário (o AD pode criá-lo desabilitado por padrão)
            conn.add(
                user_dn,
                attributes={
                    'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
                    'cn': funcionario.nome,
                    'givenName': primeiro_nome.capitalize(),
                    'sn': ' '.join(nome_parts[1:]).title(),
                    'displayName': funcionario.nome,
                    'userPrincipalName': user_principal_name,
                    'sAMAccountName': username
                }
            )

            # Passo B: Define a senha para a nova conta
            conn.extend.microsoft.modify_password(user_dn, senha_inicial)
            
            # Passo C (CORREÇÃO DEFINITIVA): Habilita a conta e força a troca de senha
            # 512 = Conta Ativa | pwdLastSet = 0 (Força troca de senha)
            conn.modify(
                user_dn,
                {
                    'userAccountControl': [(MODIFY_REPLACE, ['512'])],
                    'pwdLastSet': [(MODIFY_REPLACE, [0])]
                }
            )
        
        return True, "Operação no AD realizada com sucesso."

    except LDAPException as e:
        current_app.logger.error(f"Erro de LDAP ao provisionar/sincronizar usuário: {e}")
        return False, f"Erro de LDAP: {e}"
    finally:
        if conn:
            conn.unbind()

# (As outras funções de habilitar, desabilitar e remover continuam iguais)
def _alterar_status_usuario_ad(email, habilitar=True):
    # ... (código mantido)
    conn = get_ad_connection()
    if not conn: return False, "Falha na conexão com o AD."
    try:
        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={email})', attributes=['userAccountControl'])
        if not conn.entries: return True, "Usuário não encontrado no AD, nenhuma ação necessária."
        user_dn = conn.entries[0].entry_dn
        novo_status = '512' if habilitar else '514'
        conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [novo_status])]})
        return True, f"Usuário {email} {'habilitado' if habilitar else 'desabilitado'} no AD."
    except LDAPException as e:
        current_app.logger.error(f"Erro ao alterar status do usuário {email} no AD: {e}")
        return False, "Erro ao alterar status no AD."
    finally:
        if conn: conn.unbind()

def habilitar_usuario_ad(email):
    return _alterar_status_usuario_ad(email, habilitar=True)

def desabilitar_usuario_ad(email):
    return _alterar_status_usuario_ad(email, habilitar=False)

def remover_usuario_ad(email):
    # ... (código mantido)
    conn = get_ad_connection()
    if not conn: return False, "Falha na conexão com o AD."
    try:
        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(userPrincipalName={email})')
        if not conn.entries: return True, "Usuário não encontrado no AD, nenhuma ação necessária."
        user_dn = conn.entries[0].entry_dn
        conn.delete(user_dn)
        return True, f"Usuário {email} removido do AD com sucesso."
    except LDAPException as e:
        current_app.logger.error(f"Erro ao remover usuário {email} do AD: {e}")
        return False, "Erro ao remover usuário do AD."
    finally:
        if conn: conn.unbind()