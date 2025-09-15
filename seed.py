import json
import os
from datetime import datetime
from app import create_app, db
from app.models import Funcionario, Permissao  # <-- 1. Adicionar importação de Permissao

app = create_app()
app.app_context().push()

# --- ETAPA 1: CRIAR OU VERIFICAR PERMISSÕES ---

def criar_permissoes():
    """Cria as permissões padrão no banco de dados, se não existirem."""
    permissoes = [
        {
            'nome': 'admin_ti',
            'descricao': 'Acesso a configurações técnicas do sistema, logs e integrações.'
        },
        {
            'nome': 'admin_rh',
            'descricao': 'Acesso total ao sistema, incluindo configurações de usuários e permissões.'
        },
        {
            'nome': 'colaborador',
            'descricao': 'Acesso básico para visualizar seus próprios dados e responder a solicitações.'
        },
        # --- Novas permissões ---
        {
            'nome': 'supervisor',
            'descricao': 'Permite visualizar dados e aprovar solicitações de sua equipe direta.'
        },
        {
            'nome': 'depto_pessoal',
            'descricao': 'Acesso a rotinas de departamento pessoal, como gestão de documentos e ponto.'
        }
    ]

    print("Verificando e criando permissões...")
    for p_info in permissoes:
        permissao = Permissao.query.filter_by(nome=p_info['nome']).first()
        if not permissao:
            nova_permissao = Permissao(nome=p_info['nome'], descricao=p_info['descricao'])
            db.session.add(nova_permissao)
            print(f"  - Permissão '{p_info['nome']}' criada.")
        else:
            permissao.descricao = p_info['descricao'] # Atualiza a descrição caso já exista
            print(f"  - Permissão '{p_info['nome']}' já existe.")
    
    db.session.commit()
    print("Permissões verificadas com sucesso.")

# --- ETAPA 2: INSERIR FUNCIONÁRIOS DO JSON ---

def inserir_funcionarios():
    """Insere os funcionários a partir do arquivo funcionarios.json."""
    caminho_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json', 'funcionarios.json')
    
    try:
        with open(caminho_json, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except FileNotFoundError:
        print(f"Aviso: Arquivo {caminho_json} não encontrado. Pulando a inserção de funcionários.")
        return

    print("\nInserindo funcionários do arquivo JSON...")
    funcionarios_adicionados = 0
    for item in dados:
        # Verifica se o funcionário já existe pelo CPF para evitar duplicatas
        existe = Funcionario.query.filter_by(cpf=item["cpf"]).first()
        if not existe:
            funcionario = Funcionario(
                nome=item["nome"],
                cpf=item["cpf"],
                email=item["email"],
                telefone=item["telefone"],
                cargo=item["cargo"] or "Não informado",
                setor=item["setor"],
                data_nascimento=datetime.strptime(item["data_nascimento"], "%Y-%m-%d").date(),
                contato_emergencia_nome=item["contato_emergencia_nome"],
                contato_emergencia_telefone=item["contato_emergencia_telefone"]
            )
            db.session.add(funcionario)
            funcionarios_adicionados += 1
    
    if funcionarios_adicionados > 0:
        db.session.commit()
        print(f"{funcionarios_adicionados} funcionários novos inseridos com sucesso!")
    else:
        print("Nenhum funcionário novo para inserir. O banco de dados já está atualizado.")

# --- Execução Principal ---
if __name__ == '__main__':
    criar_permissoes()
    inserir_funcionarios()