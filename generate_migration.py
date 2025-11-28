import csv
import unidecode

# --- CONFIGURAÇÕES ---
ARQUIVO_AD = 'exportacao_ad_20251124_1527.csv'
ARQUIVO_RH = 'funcionarios.csv'
ARQUIVO_SAIDA = 'migracao_ad_full.ps1'

OU_ROOT_DN = "OU=MDR,DC=mdr,DC=local"

def normalizar(texto):
    if not texto: return ""
    return unidecode.unidecode(str(texto)).lower().strip()

# --- MAPA DE REGRAS HIERÁRQUICAS (CALIBRADO PARA SEUS GRUPOS) ---
# A ordem é CRUCIAL: O script usa o primeiro que encontrar.
# Termos mais específicos ("autor recursos") devem vir antes de genéricos ("recursos").
REGRAS_ESTRUTURA = [
    # --- 1. ADMINISTRATIVO & APOIO ---
    ("diretoria",           ["02_Administrativo", "Diretoria"]),
    ("financeiro",          ["02_Administrativo", "Financeiro"]),
    ("ti",                  ["02_Administrativo", "TI"]),
    ("tecnologia",          ["02_Administrativo", "TI"]),
    ("suporte",             ["02_Administrativo", "TI"]),
    ("marketing",           ["02_Administrativo", "Marketing"]),
    ("recepcao",            ["02_Administrativo", "Recepcao"]),
    ("rh",                  ["02_Administrativo", "RH_DP"]),
    ("recursos humanos",    ["02_Administrativo", "RH_DP"]),
    ("dp",                  ["02_Administrativo", "RH_DP"]),
    ("pessoal",             ["02_Administrativo", "RH_DP"]),
    ("adm",                 ["02_Administrativo", "Geral_Adm"]),

    # --- 2. JURÍDICO: TRABALHISTA ---
    ("trabalhista",         ["01_Juridico", "03_Trabalhista"]),

    # --- 3. JURÍDICO: ATIVO / AUTOR ---
    # Grupos específicos do Ativo devem ser capturados aqui
    ("autor negocial",      ["01_Juridico", "02_Ativo_Autor", "BB_Negocial"]),
    ("negocial",            ["01_Juridico", "02_Ativo_Autor", "BB_Negocial"]),
    
    ("autor processual",    ["01_Juridico", "02_Ativo_Autor", "BB_Processual"]),
    ("processual",          ["01_Juridico", "02_Ativo_Autor", "BB_Processual"]),
    
    ("autor recursos",      ["01_Juridico", "02_Ativo_Autor", "BB_Recursos_Autor"]),
    ("recursos autor",      ["01_Juridico", "02_Ativo_Autor", "BB_Recursos_Autor"]),
    
    ("ativos autor",        ["01_Juridico", "02_Ativo_Autor", "Ativos_Autor"]),
    
    # Genérico Autor (se sobrar alguém só com "Autor")
    ("autor",               ["01_Juridico", "02_Ativo_Autor", "Geral_Autor"]),

    # --- 4. JURÍDICO: PASSIVO / RÉU ---
    # Muitos grupos do Passivo não têm "Reu" no nome, então mapeamos direto
    ("acordos reu",         ["01_Juridico", "01_Passivo_Reu", "BB_Acordos"]),
    ("bb acordos",          ["01_Juridico", "01_Passivo_Reu", "BB_Acordos"]),
    ("acordos",             ["01_Juridico", "01_Passivo_Reu", "BB_Acordos"]),
    
    ("defesa",              ["01_Juridico", "01_Passivo_Reu", "BB_Defesa"]),
    ("contestacao",         ["01_Juridico", "01_Passivo_Reu", "BB_Defesa"]), # Sinônimo comum
    
    ("encerramento",        ["01_Juridico", "01_Passivo_Reu", "BB_Encerramento"]),
    
    ("cadastro",            ["01_Juridico", "01_Passivo_Reu", "BB_Cadastro"]),
    
    ("ativos reu",          ["01_Juridico", "01_Passivo_Reu", "Ativos_Reu"]),
    
    ("recursos reu",        ["01_Juridico", "01_Passivo_Reu", "BB_Recursos"]),
    ("bb recursos",         ["01_Juridico", "01_Passivo_Reu", "BB_Recursos"]), # Seu caso específico
    ("recursos",            ["01_Juridico", "01_Passivo_Reu", "BB_Recursos"]), # Fallback
    
    ("reu",                 ["01_Juridico", "01_Passivo_Reu", "Geral_Reu"]),

    # --- 5. ÚLTIMO RECURSO ---
    ("juridico",            ["01_Juridico", "Geral_Juridico"]),
]

def identificar_caminho_ou(texto_bruto):
    """
    Recebe um texto (Nome do Setor ou Lista de Grupos) e retorna o caminho das OUs.
    """
    if not texto_bruto: return None, []
    
    texto = normalizar(texto_bruto)
    caminho_pastas = None

    # Varre as regras: a primeira que der match ganha
    for palavra_chave, estrutura in REGRAS_ESTRUTURA:
        if palavra_chave in texto:
            caminho_pastas = estrutura
            break 
    
    if not caminho_pastas:
        return None, []

    # Gera Comandos
    comandos_criacao = []
    dn_pai_atual = OU_ROOT_DN
    
    for pasta in caminho_pastas:
        cmd = f'Garanta-OU -Nome "{pasta}" -CaminhoPai "{dn_pai_atual}"'
        comandos_criacao.append(cmd)
        dn_pai_atual = f"OU={pasta},{dn_pai_atual}"
    
    return dn_pai_atual, comandos_criacao

def inferir_cargo_da_ou(ou_string):
    """Tenta adivinhar cargo se não tiver no RH"""
    if not ou_string: return None
    norm_ou = normalizar(ou_string)
    if 'advogado' in norm_ou: return "Advogado(a)"
    if 'estagiario' in norm_ou: return "Estagiário(a)"
    if 'assistente' in norm_ou: return "Assistente Jurídico"
    if 'supervisor' in norm_ou: return "Supervisor(a)"
    if 'coordenador' in norm_ou: return "Coordenador(a)"
    if 'diretor' in norm_ou or 'sócio' in norm_ou: return "Sócio/Diretor"
    if 'suporte' in norm_ou: return "Analista de Suporte"
    return None

def main():
    print("--- 1. Carregando dados do RH ---")
    dados_rh = {}
    try:
        with open(ARQUIVO_RH, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = normalizar(row.get('E-mail'))
                nome = normalizar(row.get('Nome Completo'))
                cargo = row.get('Cargo', '').replace('<Cargo ', '').replace('>', '')
                if 'Não Informado' in cargo: cargo = ''
                setor = row.get('Setor', '').replace('<Setor ', '').replace('>', '')
                tel = row.get('Telefone', '')
                if 'Anonimizado' in tel: tel = ''
                cpf = "".join(filter(str.isdigit, row.get('CPF', ''))) if 'Anonimizado' not in row.get('CPF', '') else ''

                info = {'cargo': cargo, 'setor_origem': setor, 'telefone': tel, 'cpf': cpf}
                if email and 'anonimizado' not in email: dados_rh[email] = info
                if nome: dados_rh[nome] = info
    except FileNotFoundError:
        print(f"AVISO: {ARQUIVO_RH} não encontrado. O script usará apenas os grupos do AD.")

    print(f"   > {len(dados_rh)} registros carregados.")

    print("--- 2. Gerando Script PowerShell ---")
    comandos_ou_set = set()
    comandos_users = []
    
    try:
        with open(ARQUIVO_AD, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            
            for row in reader:
                login = row.get('Login (Usuario)')
                if not login or login in ['Administrator', 'Guest']: continue
                
                nome_ad = normalizar(row.get('Nome (Display)'))
                email_ad = normalizar(row.get('Email'))
                match = dados_rh.get(email_ad) or dados_rh.get(nome_ad)
                
                dn_destino = None
                lista_cmds_ou = []
                origem = "Triagem"
                
                # Dados finais
                cargo_final = ""
                tel_final = ""
                cpf_final = ""
                
                # --- TENTATIVA 1: SETOR DA PLANILHA RH ---
                if match:
                    cargo_final = match['cargo']
                    tel_final = match['telefone']
                    cpf_final = match['cpf']
                    # Tenta identificar a estrutura baseada no nome do setor da planilha
                    dn_destino, lista_cmds_ou = identificar_caminho_ou(match['setor_origem'])
                    if dn_destino: origem = "RH"

                # --- TENTATIVA 2: GRUPOS DO AD (REDE DE SEGURANÇA) ---
                # Se o RH falhou ou não deu match na estrutura, olha os grupos do AD
                if not dn_destino:
                    grupos = row.get('Grupos (MemberOf)', '')
                    dn_destino, lista_cmds_ou = identificar_caminho_ou(grupos)
                    if dn_destino: origem = "Grupos_AD"
                
                # --- CARGO ---
                if not cargo_final:
                    cargo_atual = row.get('Cargo Atual (Title)')
                    if cargo_atual: 
                        cargo_final = cargo_atual
                    else:
                        cargo_final = inferir_cargo_da_ou(row.get('Estrutura OUs (Onde esta)'))

                # --- SE AINDA NÃO ACHOU DESTINO -> TRIAGEM ---
                if not dn_destino:
                    dn_destino = f"OU=00_Triagem,{OU_ROOT_DN}"
                    lista_cmds_ou = [f'Garanta-OU -Nome "00_Triagem" -CaminhoPai "{OU_ROOT_DN}"']
                    origem = "Triagem"

                for c in lista_cmds_ou: comandos_ou_set.add(c)

                if row.get('Status') == 'Ativo':
                    cor = "Green" if origem == "RH" else ("Cyan" if origem == "Grupos_AD" else "Yellow")
                    
                    # Move
                    cmd_move = f'try {{ Get-ADUser -Identity "{login}" | Move-ADObject -TargetPath "{dn_destino}" -ErrorAction Stop; Write-Host "OK: {login} -> {origem}" -ForegroundColor {cor} }} catch {{ }}'
                    comandos_users.append(cmd_move)
                    
                    # Update
                    props = []
                    if cargo_final: props.append(f'-Title "{cargo_final}"')
                    if tel_final: props.append(f'-OfficePhone "{tel_final}"')
                    if cpf_final: props.append(f'-EmployeeID "{cpf_final}"')
                    
                    if props:
                        cmd_upd = f'Set-ADUser -Identity "{login}" { " ".join(props) } -ErrorAction SilentlyContinue'
                        comandos_users.append(cmd_upd)

    except FileNotFoundError:
        print(f"ERRO: {ARQUIVO_AD} não encontrado.")
        return

    # Ordena criações de OU por tamanho (Pai antes do Filho)
    cmds_ou_ordenados = sorted(list(comandos_ou_set), key=len)

    with open(ARQUIVO_SAIDA, 'w', encoding='utf-8-sig') as f:
        f.write("# --- SCRIPT HIERARQUICO MDR (BASEADO EM GRUPOS) ---\n\n")
        f.write("function Garanta-OU {\n")
        f.write("    param ($Nome, $CaminhoPai)\n")
        f.write("    $Existe = Get-ADOrganizationalUnit -Filter \"Name -eq '$Nome'\" -SearchBase $CaminhoPai -ErrorAction SilentlyContinue\n")
        f.write("    if (-not $Existe) {\n")
        f.write("        Write-Host \"Criando: $Nome\" -ForegroundColor White\n")
        f.write("        New-ADOrganizationalUnit -Name $Nome -Path $CaminhoPai\n")
        f.write("    }\n")
        f.write("}\n\n")
        
        f.write("# 1. ESTRUTURA\n")
        for cmd in cmds_ou_ordenados: f.write(cmd + "\n")
        
        f.write("\n# 2. USUARIOS\n")
        for cmd in comandos_users: f.write(cmd + "\n")

    print(f"Script gerado: {ARQUIVO_SAIDA}")

if __name__ == "__main__":
    main()