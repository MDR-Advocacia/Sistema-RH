from flask import current_app
from . import db
from .models import Usuario, Funcionario, Permissao, Cargo, Setor, Ativo
from .ad_sync import get_ad_connection, ad_timestamp_to_datetime
from sqlalchemy import func
from datetime import datetime

def extrair_setor_da_ou(dn):
    """Analisa o DN para descobrir o SETOR (OU mais específica)."""
    if not dn: return None
    partes = dn.split(',')
    ous = [p.split('=')[1] for p in partes if p.upper().strip().startswith('OU=')]
    if len(ous) >= 1: return ous[0]
    return None

def sync_ad_computers_logic():
    print("--- [DEBUG] Iniciando Sincronização de Computadores ---")
    conn = get_ad_connection()
    if not conn:
        print("ERRO: Falha na conexão com o AD.")
        return

    conn.search(
        search_base=current_app.config['LDAP_BASE_DN'],
        search_filter='(objectClass=computer)',
        attributes=['cn', 'dNSHostName', 'operatingSystem', 'description', 'lastLogonTimestamp', 'serialNumber']
    )
    
    setor_padrao = Setor.query.filter_by(nome="A Classificar (AD)").first()
    if not setor_padrao:
        setor_padrao = Setor(nome="A Classificar (AD)")
        db.session.add(setor_padrao)
        db.session.commit()

    count_novos = 0
    hosts_encontrados = []

    for entry in conn.entries:
        hostname = entry.dNSHostName.value if 'dNSHostName' in entry else entry.cn.value
        if not hostname: continue
        hosts_encontrados.append(hostname.lower())

        os_name = entry.operatingSystem.value if 'operatingSystem' in entry else 'Desconhecido'
        descricao = entry.description.value if 'description' in entry else None
        serial = entry.serialNumber.value if 'serialNumber' in entry else None
        
        raw_logon = entry.lastLogonTimestamp.value if 'lastLogonTimestamp' in entry else 0
        last_logon_dt = ad_timestamp_to_datetime(raw_logon)

        ativo_db = Ativo.query.filter(func.lower(Ativo.hostname) == func.lower(hostname)).first()

        if not ativo_db:
            ativo_db = Ativo(
                nome=hostname.split('.')[0].upper(),
                hostname=hostname,
                tipo='Desktop' if 'server' not in os_name.lower() else 'Servidor',
                setor=setor_padrao
            )
            db.session.add(ativo_db)
            count_novos += 1
        
        ativo_db.sistema_operacional = os_name
        ativo_db.descricao_ad = descricao
        ativo_db.ultimo_logon_ad = last_logon_dt
        if serial: ativo_db.numero_serie = serial
        
        dias_inativo = (datetime.now() - last_logon_dt).days if last_logon_dt else 999
        if ativo_db.status not in ['Baixado', 'Em Manutenção']:
            ativo_db.status = 'Ativo' if dias_inativo < 90 else 'Inativo/Obsoleto'

    todos_ativos = Ativo.query.filter(Ativo.status != 'Baixado').all()
    for ativo in todos_ativos:
        if ativo.hostname and ativo.hostname.lower() not in hosts_encontrados:
            ativo.status = 'Não Encontrado no AD'

    try:
        db.session.commit()
        print(f"Computadores processados. Novos: {count_novos}")
    except Exception as e:
        db.session.rollback()
        print(f"ERRO NO COMMIT DE ATIVOS: {e}")

def sync_ad_to_db_logic():
    print("--- [DEBUG] Iniciando Sincronização de USUÁRIOS ---")
    
    conn = get_ad_connection()
    if not conn:
        print("ERRO: Falha na conexão com o AD.")
        return

    search_filter = '(&(objectClass=person)(!(objectClass=computer)))'
    attributes = ['cn', 'sAMAccountName', 'displayName', 'mail', 'department', 'title', 'memberOf', 'userAccountControl', 'telephoneNumber', 'distinguishedName', 'lastLogonTimestamp']
    
    conn.search(
        search_base=current_app.config['LDAP_BASE_DN'],
        search_filter=search_filter,
        attributes=attributes
    )
    
    print(f"--- [DEBUG] AD retornou {len(conn.entries)} objetos. Processando... ---")

    permissoes_db = {p.nome: p for p in Permissao.query.all()}
    
    # Garante padrões
    setor_padrao = Setor.query.filter_by(nome="A Classificar (AD)").first()
    if not setor_padrao:
        setor_padrao = Setor(nome="A Classificar (AD)")
        db.session.add(setor_padrao)
    
    cargo_padrao = Cargo.query.filter_by(nome="Colaborador").first()
    if not cargo_padrao:
        cargo_padrao = Cargo(nome="Colaborador")
        db.session.add(cargo_padrao)
        
    db.session.flush()

    usuarios_encontrados_ad = []
    count_novos = 0
    count_atualizados = 0

    for entry in conn.entries:
        username = entry.sAMAccountName.value
        if not username: continue
        if username.lower() in ['krbtgt', 'guest', 'administrator', 'admin']: continue

        usuarios_encontrados_ad.append(username.lower())

        # --- DEBUG LOGON MELHORADO ---
        # Tenta pegar o valor de forma segura
        raw_logon = 0
        if 'lastLogonTimestamp' in entry:
            raw_logon = entry.lastLogonTimestamp.value
        
        dt_logon_ad = ad_timestamp_to_datetime(raw_logon)
        
        if dt_logon_ad:
            print(f"[DEBUG] {username}: SUCESSO - Data={dt_logon_ad}")
        else:
            # Mostra o erro para entendermos o motivo (Zero, None, ou ausente)
            # Limitamos a 5 erros para não floodar se for geral
            if count_atualizados < 5: 
                print(f"[DEBUG] {username}: FALHA - Raw={raw_logon} | Atributos retornados: {entry.entry_attributes}")
        # -----------------------------

        # Dados Básicos
        cn_val = entry.cn.value if 'cn' in entry else ''
        display_name_val = entry.displayName.value if 'displayName' in entry else ''
        nome = display_name_val or cn_val or username
        email = entry.mail.value if 'mail' in entry else None
        telefone = entry.telephoneNumber.value if 'telephoneNumber' in entry else None
        
        dn = entry.distinguishedName.value
        nome_setor_ou = extrair_setor_da_ou(dn)
        if not nome_setor_ou and 'department' in entry:
            nome_setor_ou = entry.department.value
            
        nome_cargo_attr = entry.title.value if 'title' in entry else None

        uac = entry.userAccountControl.value if 'userAccountControl' in entry else 512
        is_disabled = (uac & 2) == 2
        status_novo = 'Suspenso' if is_disabled else 'Ativo'

        # --- Tratamento de Cargo/Setor no DB ---
        obj_cargo = cargo_padrao
        if nome_cargo_attr:
            obj_cargo = Cargo.query.filter(func.lower(Cargo.nome) == func.lower(nome_cargo_attr)).first()
            if not obj_cargo:
                obj_cargo = Cargo(nome=nome_cargo_attr)
                db.session.add(obj_cargo)
                db.session.flush()
        
        obj_setor = setor_padrao
        if nome_setor_ou:
            obj_setor = Setor.query.filter(func.lower(Setor.nome) == func.lower(nome_setor_ou)).first()
            if not obj_setor:
                obj_setor = Setor(nome=nome_setor_ou)
                db.session.add(obj_setor)
                db.session.flush()

        # --- Busca/Cria Usuário ---
        usuario_db = Usuario.query.filter(func.lower(Usuario.username) == func.lower(username)).first()
        funcionario = usuario_db.funcionario if usuario_db else None
        
        if not funcionario and email:
            funcionario = Funcionario.query.filter(func.lower(Funcionario.email) == func.lower(email)).first()

        if not funcionario:
            cpf_dummy = f"AD-{username}"
            email_final = email if email else f"{username}@sem-email.local"
            
            funcionario = Funcionario(
                nome=nome,
                email=email_final,
                cpf=cpf_dummy,
                status=status_novo,
                cargo=obj_cargo,
                setor=obj_setor,
                telefone=telefone
            )
            db.session.add(funcionario)
            db.session.flush()
            
            novo_user = Usuario(username=username, email=email_final, funcionario_id=funcionario.id, senha_provisoria=False)
            novo_user.set_password("AuthAD123")
            
            # SALVANDO LOGON NOVO
            novo_user.ultimo_logon_ad = dt_logon_ad 
            
            db.session.add(novo_user)
            usuario_db = novo_user
            count_novos += 1
        else:
            # Update Existente
            funcionario.nome = nome
            funcionario.status = status_novo
            if email: funcionario.email = email
            if telefone: funcionario.telefone = telefone
            if obj_cargo and obj_cargo.id != cargo_padrao.id: funcionario.cargo = obj_cargo
            if obj_setor and obj_setor.id != setor_padrao.id: funcionario.setor = obj_setor
            
            if not funcionario.usuario:
                novo_user = Usuario(username=username, email=funcionario.email, funcionario_id=funcionario.id)
                novo_user.set_password("AuthAD123")
                
                # SALVANDO LOGON
                novo_user.ultimo_logon_ad = dt_logon_ad
                
                db.session.add(novo_user)
                usuario_db = novo_user
            else:
                usuario_db = funcionario.usuario
                usuario_db.username = username
                
                # ATUALIZANDO LOGON EXISTENTE
                if dt_logon_ad: 
                    usuario_db.ultimo_logon_ad = dt_logon_ad 
            
            count_atualizados += 1

        # --- Sincroniza Permissões ---
        if usuario_db:
            grupos = entry.memberOf.values if 'memberOf' in entry else []
            ad_group_names = {dn.split(',')[0].split('=')[1] for dn in grupos}
            
            perms_to_add = []
            
            if 'TI' in ad_group_names or 'G_Intranet_TI' in ad_group_names:
                if 'tecnico_ti' in permissoes_db: perms_to_add.append(permissoes_db['tecnico_ti'])
            
            if 'Supervisores' in ad_group_names or 'G_Intranet_Supervisores' in ad_group_names:
                if 'supervisor' in permissoes_db: perms_to_add.append(permissoes_db['supervisor'])
                
            if 'RH' in ad_group_names or 'G_Intranet_RH' in ad_group_names:
                if 'dp_pessoal' in permissoes_db: perms_to_add.append(permissoes_db['dp_pessoal'])

            eh_rh = ('RH' in ad_group_names or 'G_Intranet_RH' in ad_group_names)
            eh_sup = ('Supervisores' in ad_group_names or 'G_Intranet_Supervisores' in ad_group_names)
            eh_ti = ('TI' in ad_group_names or 'G_Intranet_TI' in ad_group_names)

            if eh_rh and eh_sup and 'admin_rh' in permissoes_db:
                perms_to_add.append(permissoes_db['admin_rh'])
            
            if eh_ti and eh_sup and 'admin_ti' in permissoes_db:
                perms_to_add.append(permissoes_db['admin_ti'])
                if 'supervisor_ti' in permissoes_db: perms_to_add.append(permissoes_db['supervisor_ti'])
            
            if 'colaborador' in permissoes_db: perms_to_add.append(permissoes_db['colaborador'])

            usuario_db.permissoes = list(set(perms_to_add))

    # --- Caça-Fantasmas ---
    print("--- Verificando usuários removidos do AD ---")
    usuarios_db_ativos = Usuario.query.join(Funcionario).filter(Usuario.username.isnot(None), Funcionario.status == 'Ativo').all()
    for u in usuarios_db_ativos:
        if u.username.lower() not in usuarios_encontrados_ad:
            u.funcionario.status = 'Desligado (AD)'
            u.funcionario.data_desligamento = datetime.utcnow().date()

    try:
        db.session.commit()
        print(f"\n--- Sincronização Finalizada ---")
        print(f"Novos: {count_novos} | Atualizados: {count_atualizados}")
        sync_ad_computers_logic()
    except Exception as e:
        db.session.rollback()
        print(f"ERRO FATAL NO COMMIT: {e}")