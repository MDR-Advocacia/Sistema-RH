import csv
import json
import os


from sqlalchemy import or_
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from .models import Funcionario, Sistema
from io import TextIOWrapper
from . import db


main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/cadastrar', methods=['GET'])
def exibir_formulario_cadastro():
    return render_template('cadastrar.html')

@main.route('/cadastrar', methods=['POST'])
def processar_cadastro():
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    cargo = request.form.get('cargo')
    setor = request.form.get('setor')
    data_nascimento = request.form.get('data_nascimento')
    contato_nome = request.form.get('contato_emergencia_nome')
    contato_telefone = request.form.get('contato_emergencia_telefone')

    if not nome or not cpf:
        return "Nome e CPF são obrigatórios", 400

    funcionario_existente = Funcionario.query.filter_by(cpf=cpf).first()
    if funcionario_existente:
        return "Funcionário com esse CPF já existe", 400

    funcionario = Funcionario(
        nome=nome,
        cpf=cpf,
        email=email,
        telefone=telefone,
        cargo=cargo,
        setor=setor,
        data_nascimento=datetime.strptime(data_nascimento, '%Y-%m-%d') if data_nascimento else None,
        contato_emergencia_nome=contato_nome,
        contato_emergencia_telefone=contato_telefone
    )

    db.session.add(funcionario)
    db.session.commit()

    return render_template('cadastrar.html', mensagem="Funcionário cadastrado com sucesso!")

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
                nome=linha.get('Nome Completo', ''),
                cpf=linha.get('CPF', ''),
                email=linha.get('E-mail', ''),
                telefone=linha.get('Telefone', ''),
                cargo=linha.get('Cargo', ''),
                setor=linha.get('Setor', ''),
                data_nascimento=datetime.strptime(linha.get('Data de Nascimento', '01/01/1900'), '%d/%m/%Y'),
                contato_emergencia_nome=linha.get('Contato de Emergencia (Nome)', ''),
                contato_emergencia_telefone=linha.get('Contato de Emergencia (Telefone)', '')
            )
            db.session.add(funcionario)
            count += 1

        db.session.commit()
        return jsonify({'success': True, 'message': f'{count} funcionários importados com sucesso!'})

    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao processar CSV: {str(e)}'})


@main.route('/api/buscar_funcionarios')
def buscar_funcionarios():
    termo = request.args.get('q', '').strip().lower()

    if not termo:
        return jsonify([])

    funcionarios = Funcionario.query.filter(
        or_(
            Funcionario.nome.ilike(f"%{termo}%"),
            Funcionario.cpf.ilike(f"%{termo}%")
        )
    ).all()

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



@main.route('/alterar_colaborador', methods=['POST'])
def alterar_colaborador_post():
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
            if campo == "data_nascimento" and valor:
                valor = datetime.strptime(valor, "%Y-%m-%d")
            setattr(funcionario, campo, valor)

    db.session.commit()

    # Sem usar flash: renderiza a página com uma mensagem
    return render_template("alterar.html", mensagem="Alterações salvas com sucesso!")

@main.route('/remover')
def deletar():
    return render_template('deletar.html')


@main.route('/remover_funcionario', methods=['POST'])
def remover_funcionario():
    cpf = request.form.get('cpf')
    if not cpf:
        return jsonify({'success': False, 'message': 'CPF não informado'}), 400

    funcionario = Funcionario.query.filter_by(cpf=cpf).first()
    if not funcionario:
        return jsonify({'success': False, 'message': 'Funcionário não encontrado'}), 404

    db.session.delete(funcionario)
    db.session.commit()
    # Redireciona para página de deletar com mensagem? Ou só retorna JSON?
    # Se preferir redirecionar, troque para redirect(url_for('main.deletar'))
    return redirect(url_for('main.deletar'))

