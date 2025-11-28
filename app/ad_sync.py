import os
import uuid
from flask import current_app
from ldap3 import Server, Connection, ALL, Tls, MODIFY_REPLACE, NTLM
from ldap3.core.exceptions import LDAPException
import ssl
from unidecode import unidecode
from datetime import datetime
# Adicione dateutil para facilitar o parsing de strings ISO
from dateutil import parser 

def get_ad_connection(user=None, password=None):
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

def ad_timestamp_to_datetime(ad_timestamp):
    """
    Converte timestamp do AD para datetime de forma robusta.
    Aceita: Inteiro (Windows FileTime), String ISO, ou datetime já pronto.
    """
    if not ad_timestamp or ad_timestamp == 0:
        return None
    
    try:
        # Caso 1: Já é um objeto datetime (o ldap3 converteu)
        if isinstance(ad_timestamp, datetime):
            return ad_timestamp

        # Caso 2: É uma string (ISO format, como no seu log)
        if isinstance(ad_timestamp, str):
            # Tenta converter string ISO
            try:
                return parser.parse(ad_timestamp)
            except:
                return None # Falhou no parse da string

        # Caso 3: É um inteiro (Windows FileTime - 100ns desde 1601)
        # 116444736000000000 é a diferença entre 1601 e 1970 em 100ns
        timestamp_seconds = (int(ad_timestamp) - 116444736000000000) / 10000000
        return datetime.fromtimestamp(timestamp_seconds)
        
    except Exception as e:
        # print(f"Erro convertendo data: {e}") # Debug opcional
        return None

def get_user_ad_info(username):
    """
    Busca informações detalhadas de um usuário no AD, INCLUINDO LAST LOGON.
    """
    conn = get_ad_connection()
    if not conn:
        return None

    try:
        search_filter = f'(&(objectClass=user)(sAMAccountName={username}))'
        attributes = ['displayName', 'mail', 'title', 'department', 'memberOf', 'lastLogonTimestamp', 'userAccountControl']
        
        conn.search(
            search_base=current_app.config['LDAP_BASE_DN'],
            search_filter=search_filter,
            attributes=attributes
        )

        if not conn.entries:
            return None

        entry = conn.entries[0]
        
        # Converte lastLogonTimestamp
        last_logon_ad = None
        if 'lastLogonTimestamp' in entry:
            # Passa o valor bruto para nossa função robusta
            last_logon_ad = ad_timestamp_to_datetime(entry.lastLogonTimestamp.value)

        return {
            'nome': str(entry.displayName.value) if 'displayName' in entry else username,
            'email': str(entry.mail.value) if 'mail' in entry else None,
            'cargo': str(entry.title.value) if 'title' in entry else None,
            'setor': str(entry.department.value) if 'department' in entry else None,
            'grupos': entry.memberOf.value if 'memberOf' in entry else [],
            'ativo_ad': not ((entry.userAccountControl.value & 2) == 2) if 'userAccountControl' in entry else True,
            'last_logon': last_logon_ad
        }
    except Exception as e:
        current_app.logger.error(f"Erro ao buscar info extendida do usuário {username}: {e}")
        return None
    finally:
        if conn:
            conn.unbind()

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

def provisionar_usuario_ad(funcionario, username_manual=None, vincular=False):
    """
    Garante que um usuário exista no AD, com suporte para username manual e vinculação.
    """
    if vincular:
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
        nome_parts = funcionario.nome.lower().split()
        primeiro_nome_unidecoded = unidecode(nome_parts[0])
        
        if username_manual:
            username = username_manual.lower()
        else:
            if len(nome_parts) > 1:
                sobrenome_unidecoded = unidecode(nome_parts[-1])
                username = f"{primeiro_nome_unidecoded}.{sobrenome_unidecoded}"
            else:
                username = primeiro_nome_unidecoded

        domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
        user_principal_name = f"{username}@{domain}"
        user_dn = f"CN={funcionario.nome},{current_app.config['LDAP_USERS_DN']}"

        conn.search(search_base=current_app.config['LDAP_BASE_DN'], search_filter=f'(sAMAccountName={username})', attributes=['cn'])

        cargo_nome = funcionario.cargo.nome if funcionario.cargo else ''
        setor_nome = funcionario.setor.nome if funcionario.setor else ''

        if conn.entries:
            user_dn_existente = conn.entries[0].entry_dn
            
            modificacoes = {
                'displayName': [(MODIFY_REPLACE, [funcionario.nome])],
                'title': [(MODIFY_REPLACE, [cargo_nome])],
                'department': [(MODIFY_REPLACE, [setor_nome])],
            }
            modificacoes_finais = {k: v for k, v in modificacoes.items() if v[0][1][0] is not None}

            if modificacoes_finais:
                conn.modify(user_dn_existente, modificacoes_finais)
        else:
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
                    'mail': funcionario.email,
                    'title': cargo_nome,
                    'department': setor_nome
                }
            )
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao criar o objeto do usuário: {conn.result['description']} - {conn.result['message']}")

            senha_padrao = current_app.config.get('AD_DEFAULT_PASSWORD')
            if not senha_padrao:
                raise LDAPException("A senha padrão do AD (AD_DEFAULT_PASSWORD) não está configurada no .env")

            quoted_password = '"' + senha_padrao + '"'
            encoded_password = quoted_password.encode('utf-16-le')

            conn.modify(user_dn, {'unicodePwd': [(MODIFY_REPLACE, [encoded_password])]})
            if not conn.result['result'] == 0:
                raise LDAPException(f"Falha ao definir a senha (verifique a política de complexidade): {conn.result['description']} - {conn.result['message']}")
            
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

def _alterar_status_usuario_ad(username, habilitar=True):
    """
    Função interna para habilitar ou desabilitar uma conta de usuário no AD.
    """
    conn = get_ad_connection()
    if not conn:
        return False, "Falha na conexão com o AD."

    try:
        search_filter = f'(sAMAccountName={username})'
        
        conn.search(
            search_base=current_app.config['LDAP_BASE_DN'], 
            search_filter=search_filter, 
            attributes=['userAccountControl']
        )
        
        if not conn.entries:
            return False, f"Usuário '{username}' não encontrado no AD."

        user_dn = conn.entries[0].entry_dn
        
        novo_status = '512' if habilitar else '514'
        
        conn.modify(user_dn, {'userAccountControl': [(MODIFY_REPLACE, [novo_status])]})

        if conn.result.get('result') == 0:
            return True, f"Usuário {username} {'habilitado' if habilitar else 'desabilitado'} com sucesso no AD."
        else:
            raise LDAPException(f"Falha ao modificar o atributo: {conn.result.get('description')}")

    except LDAPException as e:
        current_app.logger.error(f"Erro de LDAP ao alterar status do usuário {username}: {e}")
        return False, f"Erro de LDAP: {e}"
    finally:
        if conn:
            conn.unbind()

def habilitar_usuario_ad(email):
    return _alterar_status_usuario_ad(email, habilitar=True)

def desabilitar_usuario_ad(username):
    return _alterar_status_usuario_ad(username, habilitar=False)

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