import json
import os

from app import create_app, db
from app.models import Funcionario
from datetime import datetime

app = create_app()
app.app_context().push()

# Caminho para o arquivo JSON (ajuste conforme seu projeto)
caminho_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json', 'funcionarios.json')

# Abrir e carregar o JSON
with open(caminho_json, 'r', encoding='utf-8') as f:
    dados = json.load(f)

# Inserir no banco
for item in dados:
    funcionario = Funcionario(
        nome=item["nome"],
        cpf=item["cpf"],
        email=item["email"],
        telefone=item["telefone"],
        cargo=item["cargo"] or "Não informado",
        setor=item["setor"],
        data_nascimento=datetime.strptime(item["data_nascimento"], "%Y-%m-%d"),
        contato_emergencia_nome=item["contato_emergencia_nome"],
        contato_emergencia_telefone=item["contato_emergencia_telefone"]
    )
    db.session.add(funcionario)

db.session.commit()
print("Funcionários inseridos com sucesso!")
