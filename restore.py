import json
from datetime import datetime
from app import create_app, db
from app.models import Funcionario, Usuario, Permissao

app = create_app()
app.app_context().push()

def restore_data():
    """Limpa as tabelas, importa dados dos backups e sincroniza as sequências de ID."""

    # Limpa os dados existentes
    print("Limpando tabelas existentes...")
    db.session.query(Usuario).delete()
    db.session.query(Funcionario).delete()
    db.session.query(Permissao).delete()
    db.session.commit()
    print("Tabelas limpas.")

    # Restaurar Permissoes
    with open('backup_permissoes.json', 'r', encoding='utf-8') as f:
        permissoes_data = json.load(f)
    for p_data in permissoes_data:
        p = Permissao(**p_data)
        db.session.add(p)
    db.session.commit()
    print(f"{len(permissoes_data)} permissões restauradas.")

    # Restaurar Funcionarios
    with open('backup_funcionarios.json', 'r', encoding='utf-8') as f:
        funcionarios_data = json.load(f)
    for f_data in funcionarios_data:
        if f_data.get('data_nascimento'):
            f_data['data_nascimento'] = datetime.strptime(f_data['data_nascimento'], '%Y-%m-%d').date()
        f = Funcionario(**f_data)
        db.session.add(f)
    db.session.commit()
    print(f"{len(funcionarios_data)} funcionários restaurados.")

    # Restaurar Usuarios
    with open('backup_usuarios.json', 'r', encoding='utf-8') as f:
        usuarios_data = json.load(f)
    for u_data in usuarios_data:
        permissoes_nomes = u_data.pop('permissoes', [])
        user = Usuario(**u_data)
        if permissoes_nomes:
            permissoes_objs = Permissao.query.filter(Permissao.nome.in_(permissoes_nomes)).all()
            user.permissoes.extend(permissoes_objs)
        db.session.add(user)
    db.session.commit()
    print(f"{len(usuarios_data)} usuários restaurados.")

    # --- SINCRONIZAÇÃO DOS CONTADORES DE ID (NOVO) ---
    print("Sincronizando contadores de ID do PostgreSQL...")
    try:
        db.session.execute(db.text("SELECT setval('funcionario_id_seq', (SELECT MAX(id) FROM funcionario));"))
        db.session.execute(db.text("SELECT setval('usuario_id_seq', (SELECT MAX(id) FROM usuario));"))
        db.session.commit()
        print("Contadores sincronizados com sucesso!")
    except Exception as e:
        print(f"Aviso: Não foi possível sincronizar os contadores de ID. Erro: {e}")
        db.session.rollback()

if __name__ == '__main__':
    restore_data()