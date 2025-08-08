import json
from app import create_app, db
from app.models import Funcionario, Usuario, Permissao

app = create_app()
app.app_context().push()

def backup_data():
    """Exporta dados das tabelas principais para arquivos JSON."""
    
    # Backup Funcionarios
    funcionarios = Funcionario.query.all()
    funcionarios_data = [{
        'id': f.id, 'nome': f.nome, 'cpf': f.cpf, 'email': f.email,
        'telefone': f.telefone, 'cargo': f.cargo, 'setor': f.setor,
        'data_nascimento': f.data_nascimento.strftime('%Y-%m-%d') if f.data_nascimento else None,
        'contato_emergencia_nome': f.contato_emergencia_nome,
        'contato_emergencia_telefone': f.contato_emergencia_telefone,
        'foto_perfil': f.foto_perfil, 'apelido': f.apelido
    } for f in funcionarios]
    with open('backup_funcionarios.json', 'w', encoding='utf-8') as f:
        json.dump(funcionarios_data, f, indent=4, ensure_ascii=False)
    print(f"{len(funcionarios_data)} funcionários salvos em backup_funcionarios.json")

    # Backup Usuarios e suas Permissões
    usuarios = Usuario.query.all()
    usuarios_data = [{
        'id': u.id, 'email': u.email, 'password_hash': u.password_hash,
        'funcionario_id': u.funcionario_id, 'senha_provisoria': u.senha_provisoria,
        'permissoes': [p.nome for p in u.permissoes]
    } for u in usuarios]
    with open('backup_usuarios.json', 'w', encoding='utf-8') as f:
        json.dump(usuarios_data, f, indent=4, ensure_ascii=False)
    print(f"{len(usuarios_data)} usuários salvos em backup_usuarios.json")

    # Backup Permissoes
    permissoes = Permissao.query.all()
    permissoes_data = [{'id': p.id, 'nome': p.nome, 'descricao': p.descricao} for p in permissoes]
    with open('backup_permissoes.json', 'w', encoding='utf-8') as f:
        json.dump(permissoes_data, f, indent=4, ensure_ascii=False)
    print(f"{len(permissoes_data)} permissões salvas em backup_permissoes.json")


if __name__ == '__main__':
    backup_data()