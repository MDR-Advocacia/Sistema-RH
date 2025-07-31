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
        """Cria um usuário administrador inicial."""

        # 1. Verifica se o usuário já existe
        if Usuario.query.filter_by(email=email).first():
            print(f"O usuário {email} já existe.")
            return

        # 2. Cria as permissões básicas se não existirem
        permissoes_necessarias = ['admin_rh', 'admin_ti', 'colaborador']
        mapa_permissoes = {}
        for nome_permissao in permissoes_necessarias:
            permissao = Permissao.query.filter_by(nome=nome_permissao).first()
            if not permissao:
                permissao = Permissao(nome=nome_permissao, descricao=f"Permissão de {nome_permissao}")
                db.session.add(permissao)
            mapa_permissoes[nome_permissao] = permissao
        
        # Salva as permissões no banco para garantir que elas tenham IDs
        db.session.commit()

        # 3. Cria um registro de funcionário para o admin
        # Usamos o CPF como um placeholder, já que é um campo obrigatório
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
            # Salva o funcionário para garantir que ele tenha um ID
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