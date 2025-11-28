import csv
import os
from app import create_app
from app.ad_sync import get_ad_connection
from datetime import datetime

app = create_app()

def clean_attr(entry, attr_name):
    """Extrai valor de forma segura, retornando string vazia se nulo."""
    if attr_name in entry and entry[attr_name].value:
        if isinstance(entry[attr_name].value, list):
            return "; ".join(entry[attr_name].value)
        return str(entry[attr_name].value).strip()
    return ""

def format_groups(entry):
    """Limpa a lista de grupos para ficar legível (G_TI; G_RH...)."""
    if 'memberOf' not in entry or not entry.memberOf.value:
        return ""
    
    raw_groups = entry.memberOf.value
    if isinstance(raw_groups, str):
        raw_groups = [raw_groups]
        
    # Pega só o nome (CN=NomeDoGrupo,OU=...) -> NomeDoGrupo
    clean_names = []
    for g in raw_groups:
        parts = g.split(',')
        for p in parts:
            if p.upper().startswith('CN='):
                clean_names.append(p.split('=')[1])
                break
    return "; ".join(clean_names)

def get_ou_path(dn):
    """Extrai apenas a estrutura de pastas do DN."""
    # Ex: CN=Joao,OU=Suporte,OU=TI,DC=mdr,DC=local -> TI > Suporte
    if not dn: return ""
    parts = dn.split(',')
    ous = [p.split('=')[1] for p in parts if p.upper().startswith('OU=')]
    # Inverte para mostrar da raiz para a ponta (MDR > TI > Suporte)
    return " > ".join(reversed(ous))

def run_export():
    print("--- Conectando ao AD ---")
    conn = get_ad_connection()
    if not conn:
        print("ERRO: Não foi possível conectar.")
        return

    print("--- Buscando usuários ---")
    # Busca todos os usuários (pessoas)
    conn.search(
        search_base=app.config['LDAP_BASE_DN'],
        search_filter='(&(objectClass=person)(!(objectClass=computer)))',
        attributes=[
            'cn', 'sAMAccountName', 'displayName', 'mail', 
            'title', 'department', 'memberOf', 'distinguishedName',
            'userAccountControl'
        ]
    )

    filename = f"exportacao_ad_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    
    # encoding='utf-8-sig' é vital para abrir acentos corretamente no Excel
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';') # Ponto e vírgula é melhor para Excel BR
        
        # Cabeçalho
        writer.writerow([
            'Nome (Display)', 
            'Login (Usuario)', 
            'Email', 
            'Status',
            'Cargo Atual (Title)', 
            'Setor Atual (Dept)', 
            'Estrutura OUs (Onde esta)', 
            'Grupos (MemberOf)',
            'DN Completo (ID unico)'
        ])

        count = 0
        for entry in conn.entries:
            login = clean_attr(entry, 'sAMAccountName')
            if not login: continue 
            
            # Pula contas de sistema se quiser
            if login.lower() in ['krbtgt', 'guest']: continue

            # Verifica status
            uac = entry.userAccountControl.value if 'userAccountControl' in entry else 512
            status = 'Desativado' if (uac & 2) == 2 else 'Ativo'

            writer.writerow([
                clean_attr(entry, 'displayName') or clean_attr(entry, 'cn'),
                login,
                clean_attr(entry, 'mail'),
                status,
                clean_attr(entry, 'title'),
                clean_attr(entry, 'department'),
                get_ou_path(clean_attr(entry, 'distinguishedName')),
                format_groups(entry),
                clean_attr(entry, 'distinguishedName')
            ])
            count += 1

    print(f"--- Sucesso! ---")
    print(f"{count} usuários exportados para o arquivo: {filename}")
    print("Abra este arquivo no Excel/Google Sheets para planejar a mudança.")

if __name__ == "__main__":
    with app.app_context():
        run_export()