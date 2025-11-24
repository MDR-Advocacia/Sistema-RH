from flask import current_app
from . import db
from .models import Usuario, Funcionario, Permissao, Cargo, Setor
from .ad_sync import get_ad_connection
from sqlalchemy import func
from datetime import datetime

def sync_ad_to_db_logic():
    """
    Lógica isolada para espelhar o AD no Banco de Dados.
    Trata dados faltantes e sincroniza permissões.
    """
    print("--- Iniciando Espelhamento AD -> DB ---")
    
    conn = get_ad_connection()
    if not conn:
        print("ERRO: Falha na conexão com o AD.")
        return

    # 1. Busca Usuários Reais (Ignora computadores e contas de sistema)
    print("Lendo diretório (isso pode levar alguns segundos)...")
    search_filter = '(&(objectClass=person)(!(objectClass=computer)))'
    
    # CORREÇÃO: Adicionado 'cn' na lista de atributos
    conn.search(
        search_base=current_app.config['LDAP_BASE_DN'],
        search_filter=search_filter,
        attributes=['cn', 'sAMAccountName', 'displayName', 'mail', 'department', 'title', 'memberOf', 'userAccountControl', 'telephoneNumber']
    )
    
    total = len(conn.entries)
    print(f"Encontrados {total} objetos. Processando...")

    permissoes_db = {p.nome: p for p in Permissao.query.all()}
    
    setor_padrao = Setor.query.filter_by(nome="A Classificar (AD)").first()
    if not setor_padrao:
        setor_padrao = Setor(nome="A Classificar (AD)")
        db.session.add(setor_padrao)
        db.session.commit()

    count_novos = 0
    count_atualizados = 0

    for entry in conn.entries:
        username = entry.sAMAccountName.value
        if not username: continue
        
        if username.lower() in ['krbtgt', 'guest', 'administrator', 'admin']: continue

        # Uso seguro dos atributos (se não vier, usa None ou string vazia)
        # Agora 'cn' virá corretamente porque pedimos na busca acima
        cn_val = entry.cn.value if 'cn' in entry else ''
        display_name_val = entry.displayName.value if 'displayName' in entry else ''
        
        nome = display_name_val or cn_val or username
        email = entry.mail.value if 'mail' in entry else None
        cargo_nome = entry.title.value if 'title' in entry else None
        setor_nome = entry.department.value if 'department' in entry else None
        telefone = entry.telephoneNumber.value if 'telephoneNumber' in entry else None
        
        # userAccountControl é obrigatório, mas vamos garantir
        uac = entry.userAccountControl.value if 'userAccountControl' in entry else 512
        grupos = entry.memberOf.values if 'memberOf' in entry else []

        is_disabled = (uac & 2) == 2
        status_novo = 'Suspenso' if is_disabled else 'Ativo'

        # --- TRATAMENTO DE CARGO E SETOR ---
        obj_cargo = None
        if cargo_nome:
            obj_cargo = Cargo.query.filter(func.lower(Cargo.nome) == func.lower(cargo_nome)).first()
            if not obj_cargo:
                obj_cargo = Cargo(nome=cargo_nome)
                db.session.add(obj_cargo)
                db.session.flush()
        
        obj_setor = setor_padrao
        if setor_nome:
            obj_setor = Setor.query.filter(func.lower(Setor.nome) == func.lower(setor_nome)).first()
            if not obj_setor:
                obj_setor = Setor(nome=setor_nome)
                db.session.add(obj_setor)
                db.session.flush()

        # --- BUSCA DO FUNCIONÁRIO ---
        usuario_db = Usuario.query.filter(func.lower(Usuario.username) == func.lower(username)).first()
        funcionario = usuario_db.funcionario if usuario_db else None

        if not funcionario and email:
            funcionario = Funcionario.query.filter(func.lower(Funcionario.email) == func.lower(email)).first()

        # --- CRIAÇÃO OU ATUALIZAÇÃO ---
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
            
            novo_user = Usuario(
                username=username,
                email=email_final,
                funcionario_id=funcionario.id,
                senha_provisoria=False
            )
            novo_user.set_password("AuthAD123")
            db.session.add(novo_user)
            usuario_db = novo_user
            
            count_novos += 1
        else:
            funcionario.nome = nome
            if email: funcionario.email = email
            if telefone: funcionario.telefone = telefone
            if obj_cargo: funcionario.cargo = obj_cargo
            if obj_setor and obj_setor.id != setor_padrao.id: funcionario.setor = obj_setor
            
            funcionario.status = status_novo
            
            if not funcionario.usuario:
                novo_user = Usuario(username=username, email=funcionario.email, funcionario_id=funcionario.id)
                novo_user.set_password("AuthAD123")
                db.session.add(novo_user)
                usuario_db = novo_user
            else:
                usuario_db = funcionario.usuario
                if usuario_db.username.lower() != username.lower():
                    usuario_db.username = username

            count_atualizados += 1

        # --- SINCRONIZAÇÃO DE PERMISSÕES ---
        if usuario_db:
            ad_group_names = {dn.split(',')[0].split('=')[1] for dn in grupos}
            
            perms_to_add = []
            
            if 'TI' in ad_group_names and 'tecnico_ti' in permissoes_db:
                perms_to_add.append(permissoes_db['tecnico_ti'])
            
            if 'Supervisores' in ad_group_names and 'supervisor' in permissoes_db:
                perms_to_add.append(permissoes_db['supervisor'])
            
            if ('Recursos Humanos' in ad_group_names or 'Departamento Pessoal' in ad_group_names) and 'dp_pessoal' in permissoes_db:
                perms_to_add.append(permissoes_db['dp_pessoal'])

            if 'Recursos Humanos' in ad_group_names and 'Supervisores' in ad_group_names and 'admin_rh' in permissoes_db:
                perms_to_add.append(permissoes_db['admin_rh'])

            if 'TI' in ad_group_names and 'Supervisores' in ad_group_names and 'admin_ti' in permissoes_db:
                perms_to_add.append(permissoes_db['admin_ti'])
            
            if 'supervisor_ti' in permissoes_db and 'TI' in ad_group_names and 'Supervisores' in ad_group_names:
                perms_to_add.append(permissoes_db['supervisor_ti'])

            if 'colaborador' in permissoes_db:
                perms_to_add.append(permissoes_db['colaborador'])

            usuario_db.permissoes = list(set(perms_to_add))

    try:
        db.session.commit()
        print(f"\n--- Sincronização Finalizada ---")
        print(f"Novos: {count_novos} | Atualizados: {count_atualizados}")
    except Exception as e:
        db.session.rollback()
        print(f"ERRO FATAL NO COMMIT: {e}")