import getpass
from app import create_app, db
from app.models import Usuario, Funcionario, Permissao

app = create_app()

with app.app_context():
    print("--- Criando Usuário Administrador Local ---")
    
    admin_username = 'admin'
    admin_email = 'admin@local.host'
    admin_cpf = '00000000000' # CPF fictício
    
    if Usuario.query.filter_by(username=admin_username).first() or Funcionario.query.filter_by(cpf=admin_cpf).first():
        print(f"Erro: O usuário '{admin_username}' ou um funcionário com CPF '{admin_cpf}' já existe.")
    else:
        try:
            password = getpass.getpass('Digite a senha para o administrador: ')
            password_confirm = getpass.getpass('Confirme a senha: ')

            if password != password_confirm:
                print("As senhas não coincidem. Operação cancelada.")
            elif not password:
                print("A senha não pode ser vazia. Operação cancelada.")
            else:
                admin_funcionario = Funcionario(
                    nome='Administrador do Sistema',
                    cpf=admin_cpf,
                    email=admin_email,
                    status='Ativo'
                )
                db.session.add(admin_funcionario)
                db.session.flush()

                # --- CORREÇÃO APLICADA AQUI ---
                # 1. Cria o usuário sem a senha
                admin_user = Usuario(
                    username=admin_username,
                    email=admin_email,
                    funcionario_id=admin_funcionario.id
                )
                # 2. Define a senha usando o método do modelo
                admin_user.set_password(password)
                # --- FIM DA CORREÇÃO ---

                permissao_ti = Permissao.query.filter_by(nome='admin_ti').first()
                if not permissao_ti:
                    print("Criando permissão 'admin_ti'...")
                    permissao_ti = Permissao(nome='admin_ti', descricao='Administrador de TI')
                    db.session.add(permissao_ti)
                
                admin_user.permissoes.append(permissao_ti)
                
                db.session.add(admin_user)
                db.session.commit()
                
                print(f"Usuário '{admin_username}' criado com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"Ocorreu um erro: {e}")