import csv
import io
from flask import current_app
from ldap3 import MODIFY_REPLACE
from .ad_sync import get_ad_connection
from .utils_normalization import limpar_cpf, limpar_telefone, limpar_cargo, limpar_setor

def processar_upload_csv_ad(arquivo_csv):
    """
    Lê o CSV, busca usuários no AD com travas de segurança contra homônimos.
    Prioridade de Busca: 1. E-mail | 2. Nome Completo (Exato)
    """
    conn = get_ad_connection()
    if not conn:
        return ["ERRO CRÍTICO: Não foi possível conectar ao AD para escrita."]

    logs = []
    
    # Lê o CSV da memória
    stream = io.StringIO(arquivo_csv.stream.read().decode("utf-8"), newline=None)
    csv_input = csv.DictReader(stream)
    
    contador_sucesso = 0
    contador_erro = 0
    contador_ambiguo = 0
    
    for row in csv_input:
        nome = row.get('Nome Completo', '').strip()
        email_csv = row.get('E-mail', '').strip()
        
        if not nome: continue

        usuario_encontrado = None
        metodo_encontro = ""

        # --- ESTRATÉGIA 1: BUSCA POR EMAIL (Alta Confiança) ---
        # Só busca se o email for válido e não for "Anonimizado"
        if email_csv and '@' in email_csv and 'Anonimizado' not in email_csv:
            conn.search(
                search_base=current_app.config['LDAP_BASE_DN'],
                search_filter=f'(&(objectClass=user)(mail={email_csv}))',
                attributes=['distinguishedName', 'title', 'department', 'telephoneNumber', 'employeeID', 'mail', 'displayName']
            )
            if len(conn.entries) == 1:
                usuario_encontrado = conn.entries[0]
                metodo_encontro = "E-mail"
            # Se achar mais de 1 email igual (raro, mas possível), ignoramos por segurança na etapa 1

        # --- ESTRATÉGIA 2: BUSCA POR NOME (Média Confiança) ---
        # Só executamos se não achou por email
        if not usuario_encontrado:
            # Tenta displayName exato
            conn.search(
                search_base=current_app.config['LDAP_BASE_DN'],
                search_filter=f'(&(objectClass=user)(displayName={nome}))',
                attributes=['distinguishedName', 'title', 'department', 'telephoneNumber', 'employeeID', 'mail', 'displayName']
            )
            
            resultados = conn.entries
            
            if len(resultados) == 1:
                usuario_encontrado = resultados[0]
                metodo_encontro = "Nome Completo"
            elif len(resultados) > 1:
                # TRAVA DE SEGURANÇA: HOMÔNIMOS
                logs.append(f"PERIGO: Nome '{nome}' é ambíguo. Encontrados {len(resultados)} usuários no AD com esse nome. Ignorado para evitar conflito.")
                contador_ambiguo += 1
                continue

        # --- SE AINDA NÃO ACHOU ---
        if not usuario_encontrado:
            logs.append(f"ALERTA: Usuário '{nome}' (Email: {email_csv}) não encontrado no AD.")
            contador_erro += 1
            continue

        # --- PREPARAÇÃO DOS DADOS (Com limpeza) ---
        changes = {}
        usuario_dn = usuario_encontrado.entry_dn
        
        # Cargo
        novo_cargo = limpar_cargo(row.get('Cargo'))
        cargo_atual = str(usuario_encontrado.title.value) if usuario_encontrado.title else ''
        if novo_cargo and novo_cargo != cargo_atual:
            changes['title'] = [(MODIFY_REPLACE, [novo_cargo])]

        # Setor
        novo_setor = limpar_setor(row.get('Setor'))
        setor_atual = str(usuario_encontrado.department.value) if usuario_encontrado.department else ''
        if novo_setor and novo_setor != setor_atual:
            changes['department'] = [(MODIFY_REPLACE, [novo_setor])]

        # Telefone
        novo_tel = limpar_telefone(row.get('Telefone'))
        tel_atual = str(usuario_encontrado.telephoneNumber.value) if usuario_encontrado.telephoneNumber else ''
        if novo_tel and novo_tel != tel_atual:
            changes['telephoneNumber'] = [(MODIFY_REPLACE, [novo_tel])]

        # CPF (Mapeado para employeeID)
        novo_cpf = limpar_cpf(row.get('CPF'))
        cpf_atual = str(usuario_encontrado.employeeID.value) if usuario_encontrado.employeeID else ''
        
        if novo_cpf and novo_cpf != cpf_atual:
            # Só atualiza se o campo no AD estiver vazio ou diferente, E se o CPF novo for válido
            changes['employeeID'] = [(MODIFY_REPLACE, [novo_cpf])]

        # --- EXECUÇÃO ---
        if changes:
            try:
                conn.modify(usuario_dn, changes)
                if conn.result['result'] == 0:
                    campos = ", ".join(changes.keys())
                    logs.append(f"SUCESSO ({metodo_encontro}): '{nome}' atualizado. [{campos}]")
                    contador_sucesso += 1
                else:
                    logs.append(f"ERRO AD: Falha ao atualizar '{nome}': {conn.result['description']}")
            except Exception as e:
                logs.append(f"ERRO PYTHON: Exceção em '{nome}': {str(e)}")
        else:
            # Opcional: Descomentar para ver quem já estava certo
            # logs.append(f"INFO: '{nome}' já está atualizado.")
            pass

    logs.append("--- RELATÓRIO FINAL ---")
    logs.append(f"Atualizados com Sucesso: {contador_sucesso}")
    logs.append(f"Não Encontrados: {contador_erro}")
    logs.append(f"Ignorados por Ambiguidade (Homônimos): {contador_ambiguo}")
    
    return logs