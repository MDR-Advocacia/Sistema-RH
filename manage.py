import click
from flask.cli import with_appcontext
from app import db
from app.models import Usuario, Funcionario, Permissao

# Esta função será registrada com o app no run.py
def register_commands(app):
    @app.cli.command("create-admin")
    @click.argument("email")
    @click.argument("senha")
    @with_appcontext
    def create_admin(email, senha):
        """Cria um usuário administrador inicial e garante que todas as permissões existam."""

        # 1. Verifica se o usuário já existe
        if Usuario.query.filter_by(email=email).first():
            print(f"O usuário {email} já existe.")
            # Mesmo que o usuário exista, continuamos para garantir que as permissões estão atualizadas.
        
        # --- CORREÇÃO APLICADA AQUI ---
        # 2. Garante que TODAS as permissões necessárias existam no sistema
        permissoes_necessarias = {
            'admin_rh': 'Acesso total ao sistema, incluindo configurações de usuários e permissões.',
            'admin_ti': 'Acesso a configurações técnicas do sistema, logs e integrações.',
            'colaborador': 'Acesso básico para visualizar seus próprios dados e responder a solicitações.',
            'supervisor': 'Permite visualizar dados e aprovar solicitações de sua equipe direta.',
            'depto_pessoal': 'Acesso a rotinas de departamento pessoal, como gestão de documentos e ponto.'
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
                permissao.descricao = desc # Atualiza a descrição se já existir
                print(f"  - Permissão '{nome}' já existe.")
            mapa_permissoes[nome] = permissao
        
        # Salva as permissões no banco para garantir que elas tenham IDs
        db.session.commit()
        print("Permissões verificadas com sucesso.")

        # Se o usuário admin já existe, não precisamos criá-lo de novo.
        if Usuario.query.filter_by(email=email).first():
            return

        # 3. Cria um registro de funcionário para o admin
        cpf_admin = "000.000.000-00"
        funcionario_admin = Funcionario.query.filter_by(cpf=cpf_admin).first()
        if not funcionario_admin:
            funcionario_admin = Funcionario(
                nome="Administrador do Sistema",
                cpf=cpf_admin,
                email=email,
                cargo="Administrador",
                setor="TI/RH"
            )
            db.session.add(funcionario_admin)
            db.session.commit()

        # 4. Cria o objeto do usuário
        user = Usuario(
            email=email,
            funcionario_id=funcionario_admin.id
        )
        user.set_password(senha)

        # 5. Associa as permissões de admin ao usuário
        user.permissoes.append(mapa_permissoes['admin_rh'])
        user.permissoes.append(mapa_permissoes['admin_ti'])

        db.session.add(user)
        db.session.commit()

        print(f"Usuário administrador {email} criado com sucesso!")

    @app.cli.command("fix-ad-emails")
    @click.option('--dry-run', is_flag=True, help='Mostra quais e-mails seriam corrigidos sem salvar no banco.')
    def fix_ad_emails(dry_run):
        """
        Corrige os e-mails de funcionários que foram sobrescritos incorretamente pelo e-mail do AD.
        Ele usa o e-mail da tabela Usuario como a fonte da verdade.
        """
        from app.models import Funcionario, Usuario, db
        from flask import current_app

        # Extrai o domínio local do AD a partir da configuração
        try:
            domain = '.'.join([dc.split('=')[1] for dc in current_app.config['LDAP_BASE_DN'].split(',')])
            ad_domain_pattern = f"%@{domain.lower()}"
        except Exception as e:
            print(f"ERRO: Não foi possível determinar o domínio do AD a partir de LDAP_BASE_DN. Verifique seu .env. Erro: {e}")
            return

        print(f"Procurando por funcionários com e-mails terminando em '{ad_domain_pattern}'...")

        # 1. Encontra funcionários cujo e-mail é do AD, mas o e-mail do usuário vinculado é diferente
        funcionarios_para_corrigir = db.session.query(Funcionario, Usuario).join(
            Usuario, Funcionario.id == Usuario.funcionario_id
        ).filter(
            Funcionario.email.ilike(ad_domain_pattern),
            Funcionario.email != Usuario.email
        ).all()

        if not funcionarios_para_corrigir:
            print("\nNenhum funcionário com e-mail incorreto encontrado. Tudo certo!")
            return

        print(f"\nEncontrados {len(funcionarios_para_corrigir)} funcionário(s) para corrigir:")
        print("-" * 50)

        count = 0
        # 2. Itera sobre os resultados para mostrar e/ou corrigir
        for funcionario, usuario in funcionarios_para_corrigir:
            email_antigo = funcionario.email
            email_novo = usuario.email
            
            print(f"Funcionário: {funcionario.nome}")
            print(f"  -> E-mail incorreto: {email_antigo}")
            print(f"  -> E-mail correto (será aplicado): {email_novo}\n")
            
            if not dry_run:
                funcionario.email = email_novo
                count += 1
                
        # 3. Salva as alterações no banco de dados se não for um dry-run
        if not dry_run:
            try:
                db.session.commit()
                print("-" * 50)
                print(f"\nSUCESSO: {count} registro(s) de funcionário(s) foram corrigidos no banco de dados.")
            except Exception as e:
                db.session.rollback()
                print(f"\nERRO: Ocorreu um problema ao salvar as alterações no banco de dados: {e}")
        else:
            print("-" * 50)
            print("\nDry-run finalizado. Nenhuma alteração foi salva no banco de dados.")
