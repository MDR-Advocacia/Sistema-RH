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