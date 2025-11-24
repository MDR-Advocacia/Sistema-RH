import click
from flask.cli import with_appcontext
# CORREÇÃO: Imports Absolutos (sem o ponto na frente)
from app import db
from app.models import Usuario, Funcionario, Permissao, Cargo, Setor, CategoriaTI, Ativo
from app.ad_mirror import sync_ad_to_db_logic

# Esta função será registrada com o app no run.py
def register_commands(app):
    
    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("senha")
    @with_appcontext
    def create_admin(email, senha):
        """Cria um usuário administrador inicial e garante que todas as permissões existam."""

        # 1. Verifica se o usuário já existe
        user_existe = Usuario.query.filter_by(email=email).first()
        if user_existe:
            print(f"O usuário {email} já existe.")
        
        # 2. Garante que TODAS as permissões necessárias existam no sistema
        permissoes_necessarias = {
            'admin_rh': 'Admin do RH (RH + Supervisor).',
            'admin_ti': 'Acesso a configurações técnicas do sistema, logs e integrações.',
            'colaborador': 'Acesso básico para visualizar seus próprios dados e responder a solicitações.',
            'supervisor': 'Permissão base para supervisores de qualquer setor.',
            'dp_pessoal': 'Acesso a rotinas de departamento pessoal.',
            'tecnico_ti': 'Permissão base para membros da TI.',
            'supervisor_ti': 'Admin da TI (TI + Supervisor).'
        }
        
        print("Verificando e criando permissões...")
        mapa_permissoes = {}
        for nome, desc in permissoes_necessarias.items():
            permissao = Permissao.query.filter_by(nome=nome).first()
            if not permissao:
                permissao = Permissao(nome=nome, descricao=desc)
                db.session.add(permissao)
                print(f"  - Permissão '{nome}' criada.")
            else:
                # Atualiza descrição se necessário
                permissao.descricao = desc
            mapa_permissoes[nome] = permissao
        
        db.session.commit()
        print("Permissões verificadas com sucesso.")

        # Verifica Setor e Cargo do Admin (Evita erro de chave estrangeira)
        print("Verificando Setor e Cargo do Admin...")
        setor_admin = Setor.query.filter_by(nome="TI").first()
        if not setor_admin:
            setor_admin = Setor(nome="TI")
            db.session.add(setor_admin)
            print("  - Setor 'TI' criado.")

        cargo_admin = Cargo.query.filter_by(nome="Administrador").first()
        if not cargo_admin:
            cargo_admin = Cargo(nome="Administrador")
            db.session.add(cargo_admin)
            print("  - Cargo 'Administrador' criado.")
        
        db.session.commit()

        if user_existe:
            return

        # 3. Cria um registro de funcionário para o admin
        cpf_admin = "000.000.000-00"
        funcionario_admin = Funcionario.query.filter_by(cpf=cpf_admin).first()
        if not funcionario_admin:
            funcionario_admin = Funcionario(
                nome="Administrador do Sistema",
                cpf=cpf_admin,
                email=email,
                cargo=cargo_admin,
                setor=setor_admin
            )
            db.session.add(funcionario_admin)
            db.session.flush() 
            
            # 4. Cria o usuário
            user = Usuario(
                email=email,
                funcionario_id=funcionario_admin.id,
                username=email.split('@')[0]
            )
            user.set_password(senha)

            # 5. Associa permissões
            if 'admin_rh' in mapa_permissoes: user.permissoes.append(mapa_permissoes['admin_rh'])
            if 'admin_ti' in mapa_permissoes: user.permissoes.append(mapa_permissoes['admin_ti'])
            if 'supervisor_ti' in mapa_permissoes: user.permissoes.append(mapa_permissoes['supervisor_ti'])

            db.session.add(user)
            db.session.commit()
            print(f"Usuário administrador {email} criado com sucesso!")

    @app.cli.command("fix-ad-emails")
    @click.option('--dry-run', is_flag=True, help='Mostra quais e-mails seriam corrigidos sem salvar no banco.')
    def fix_ad_emails(dry_run):
        """
        Corrige os e-mails de funcionários que foram sobrescritos incorretamente pelo e-mail do AD.
        """
        from app.models import Funcionario, Usuario
        from flask import current_app
        try:
            domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
            ad_domain_pattern = f"%@{domain.lower()}"
        except Exception as e:
            print(f"ERRO: Verifique LDAP_BASE_DN no .env. {e}")
            return

        print(f"Procurando por funcionários com e-mails terminando em '{ad_domain_pattern}'...")

        funcionarios = db.session.query(Funcionario, Usuario).join(
            Usuario, Funcionario.id == Usuario.funcionario_id
        ).filter(
            Funcionario.email.ilike(ad_domain_pattern),
            Funcionario.email != Usuario.email
        ).all()

        if not funcionarios:
            print("\nNenhum funcionário com e-mail incorreto encontrado.")
            return

        count = 0
        for f, u in funcionarios:
            print(f"Corrigindo: {f.nome} | {f.email} -> {u.email}")
            if not dry_run:
                f.email = u.email
                count += 1
        
        if not dry_run:
            db.session.commit()
            print(f"\nSUCESSO: {count} registros corrigidos.")
        else:
            print("\nDry-run finalizado.")

    @app.cli.command("seed-helpdesk")
    @with_appcontext
    def seed_helpdesk_command():
        """Popula o banco com categorias de TI iniciais."""
        categorias = [
            "Hardware (Computador, Notebook, Monitor)",
            "Software (Sistema, E-mail, Office)",
            "Rede (Internet, Wi-Fi, VPN)",
            "Impressoras e Periféricos",
            "Sistemas Internos (LegalOne, RH, etc.)",
            "Acessos e Senhas",
            "Outras Solicitações"
        ]
        count = 0
        for c in categorias:
            if not CategoriaTI.query.filter_by(nome=c).first():
                db.session.add(CategoriaTI(nome=c))
                count += 1
        db.session.commit()
        print(f"{count} categorias criadas.")

    @app.cli.command("seed-ativos")
    @with_appcontext
    def seed_ativos_command():
        """Cria ativos fictícios para teste."""
        ativos = [
            ("MDR-NOT01", "Notebook Dell Latitude 5420"),
            ("MDR-DESK05", "Desktop Lenovo ThinkCentre"),
            ("MDR-IMP02", "Impressora Brother Laser"),
            ("MDR-SERV01", "Servidor de Arquivos")
        ]
        for tag, nome in ativos:
            if not Ativo.query.filter_by(tag_patrimonio=tag).first():
                # Cria ativo 'solto' (sem setor) para teste inicial
                db.session.add(Ativo(nome=nome, tag_patrimonio=tag, hostname=tag))
        db.session.commit()
        print("Ativos de teste criados.")

    # --- NOVO COMANDO: SINCRONIZAÇÃO TOTAL COM AD (DUMPZÃO) ---
    @app.cli.command("sync-ad-db")
    @with_appcontext
    def sync_ad_db_command():
        """Executa a sincronização completa do AD (Pessoas, Cargos, Setores)."""
        sync_ad_to_db_logic()