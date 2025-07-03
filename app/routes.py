import csv
import json
import os

from flask import Blueprint, request, jsonify, render_template
from .models import Funcionario, Sistema
from io import TextIOWrapper
from . import db
from datetime import datetime

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/cadastrar', methods=['POST'])
def cadastrar():
    data = request.get_json()
    funcionario = Funcionario(
        nome=data['nome'],
        cpf=data['cpf'],
        cargo=data['cargo'],
        setor=data['setor'],
        email=data['email'],
        data_admissao=datetime.strptime(data['data_admissao'], '%Y-%m-%d')
    )
    db.session.add(funcionario)
    db.session.commit()

    for nome_sistema in data['sistemas']:
        sistema = Sistema(nome=nome_sistema, status='ativo', funcionario_id=funcionario.id)
        db.session.add(sistema)

    db.session.commit()
    return jsonify({'message': 'Funcionário cadastrado com sucesso!'})

@main.route('/funcionarios')
def listar_funcionarios():
    termo_busca = request.args.get('q', '').strip().lower()

    # Começa com todos os funcionários
    funcionarios = Funcionario.query.all()

    if termo_busca:
        funcionarios = [
            f for f in funcionarios
            if termo_busca in f.nome.lower()
            or termo_busca in f.cpf
            or termo_busca in f.setor.lower()
        ]

    return render_template('funcionarios.html', funcionarios=funcionarios)




@main.route('/sistemas')
def listar_sistemas():
    sistemas = Sistema.query.all()
    return render_template('sistemas.html', sistemas=sistemas)

@main.route('/importar_csv', methods=['POST'])
def importar_csv():
    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'})

    arquivo = request.files['arquivo']
    if not arquivo.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Formato inválido. Envie um arquivo .csv.'})

    try:
        arquivo_csv = TextIOWrapper(arquivo, encoding='utf-8')
        leitor = csv.DictReader(arquivo_csv)

        count = 0
        for linha in leitor:
            if not linha.get('CPF'):
                continue

            existente = Funcionario.query.filter_by(cpf=linha['CPF']).first()
            if existente:
                continue

            funcionario = Funcionario(
                nome=linha.get('Nome completo', ''),
                cpf=linha.get('CPF', ''),
                email=linha.get('Email', ''),
                telefone=linha.get('Telefone', ''),
                cargo=linha.get('Cargo', ''),
                setor=linha.get('Setor', ''),
                data_nascimento=datetime.strptime(linha.get('Data nascimento', '01/01/1900'), '%d/%m/%Y'),
                contato_emergencia_nome=linha.get('Nome contato emergência', ''),
                contato_emergencia_telefone=linha.get('Telefone contato emergência', '')
            )
            db.session.add(funcionario)
            count += 1

        db.session.commit()
        return jsonify({'success': True, 'message': f'{count} funcionários importados com sucesso!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao processar CSV: {str(e)}'})

@main.route('/cadastrar', methods=['GET'])
def form_cadastrar():
    return render_template('cadastrar.html')

@main.route('/api/buscar_funcionarios')
def buscar_funcionarios():
    termo = request.args.get('q', '').strip().lower()

    if not termo:
        return jsonify([])

    funcionarios = Funcionario.query.filter(Funcionario.nome.ilike(f"%{termo}%")).all()

    resultado = []
    for f in funcionarios:
        resultado.append({
            "nome": f.nome,
            "cpf": f.cpf,
            "email": f.email,
            "telefone": f.telefone,
            "cargo": f.cargo,
            "setor": f.setor,
            "data_nascimento": f.data_nascimento.strftime("%Y-%m-%d") if f.data_nascimento else "",
            "contato_emergencia_nome": f.contato_emergencia_nome,
            "contato_emergencia_telefone": f.contato_emergencia_telefone
        })

    return jsonify(resultado)

@main.route('/alterar')
def alterar_colaborador():
    return render_template("alterar.html")

@main.route('/alterar', methods=['POST'])
def salvar_alteracoes():
    cpf = request.form.get("cpf")
    funcionario = Funcionario.query.filter_by(cpf=cpf).first()

    if not funcionario:
        return "Funcionário não encontrado", 404

    campos = [
        'nome', 'email', 'telefone', 'cargo', 'setor',
        'data_nascimento', 'contato_emergencia_nome', 'contato_emergencia_telefone'
    ]

    for campo in campos:
        if campo in request.form:
            valor = request.form.get(campo)
            if campo == "data_nascimento":
                valor = datetime.strptime(valor, "%Y-%m-%d")
            setattr(funcionario, campo, valor)

    db.session.commit()
    return render_template("alterar.html", mensagem="Alterações salvas com sucesso!")

