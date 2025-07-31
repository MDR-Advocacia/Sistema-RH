import csv
import json
import os


from sqlalchemy import or_
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response
from .models import Funcionario, Sistema
from io import TextIOWrapper, StringIO
from . import db
from flask_login import login_required
from .models import Aviso, LogCienciaAviso
from .decorators import permission_required
from flask_login import current_user


main = Blueprint('main', __name__)

@main.route('/')
@login_required # <-- Adicione esta linha para proteger a rota
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


@main.route('/exportar_csv')
def exportar_csv():
    termo_busca = request.args.get('q', '').strip().lower()

    funcionarios_query = Funcionario.query
    if termo_busca:
        funcionarios_query = funcionarios_query.filter(
            or_(
                Funcionario.nome.ilike(f"%{termo_busca}%"),
                Funcionario.cpf.ilike(f"%{termo_busca}%"),
                Funcionario.setor.ilike(f"%{termo_busca}%")
            )
        )
    
    funcionarios = funcionarios_query.all()

    # Cria um arquivo CSV em memória
    output = StringIO()
    writer = csv.writer(output)
    
    # Escreve o cabeçalho
    writer.writerow([
        'Nome Completo', 'CPF', 'E-mail', 'Telefone', 'Cargo', 'Setor',
        'Data de Nascimento', 'Contato de Emergencia (Nome)', 'Contato de Emergencia (Telefone)'
    ])

    # Escreve os dados dos funcionários
    for f in funcionarios:
        writer.writerow([
            f.nome, f.cpf, f.email, f.telefone, f.cargo, f.setor,
            f.data_nascimento.strftime('%d/%m/%Y') if f.data_nascimento else '',
            f.contato_emergencia_nome, f.contato_emergencia_telefone
        ])

    output.seek(0)

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=funcionarios.csv"
    response.headers["Content-type"] = "text/csv"

    return response

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
            "id": f.id, 
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


# --- ROTAS DO MURAL DE AVISOS ---

@main.route('/avisos')
@login_required
def listar_avisos():
    """Exibe o mural de avisos para o usuário logado."""
    todos_avisos = Aviso.query.order_by(Aviso.data_publicacao.desc()).all()
    
    # Pega os IDs dos avisos que o usuário já deu ciência
    avisos_lidos_ids = {log.aviso_id for log in current_user.logs_ciencia}

    return render_template('avisos/listar_avisos.html', 
                           avisos=todos_avisos, 
                           avisos_lidos_ids=avisos_lidos_ids)

@main.route('/avisos/novo', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh') # Apenas quem tem essa permissão pode acessar
def criar_aviso():
    """Formulário e lógica para criar um novo aviso."""
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')

        if not titulo or not conteudo:
            flash('Título e conteúdo são obrigatórios.')
            return redirect(url_for('main.criar_aviso'))

        novo_aviso = Aviso(
            titulo=titulo,
            conteudo=conteudo,
            autor_id=current_user.id
        )
        db.session.add(novo_aviso)
        db.session.commit()

        flash('Aviso publicado com sucesso!')
        return redirect(url_for('main.listar_avisos'))

    return render_template('avisos/criar_aviso.html')

@main.route('/avisos/<int:aviso_id>/ciencia', methods=['POST'])
@login_required
def dar_ciencia_aviso(aviso_id):
    """Registra que o usuário deu ciência em um aviso."""
    aviso = Aviso.query.get_or_404(aviso_id)
    
    # Verifica se já não existe um log de ciência para este usuário e aviso
    ja_deu_ciencia = LogCienciaAviso.query.filter_by(
        usuario_id=current_user.id,
        aviso_id=aviso.id
    ).first()

    if not ja_deu_ciencia:
        log = LogCienciaAviso(
            usuario_id=current_user.id,
            aviso_id=aviso.id
        )
        db.session.add(log)
        db.session.commit()
        flash(f'Ciência registrada para o aviso "{aviso.titulo}".')

    return redirect(url_for('main.listar_avisos'))

@main.route('/aviso/<int:aviso_id>/logs')
@login_required
@permission_required('admin_rh') # Apenas RH pode ver os logs
def ver_logs_ciencia(aviso_id):
    """
    Exibe a lista de todos os usuários que deram ciência em um aviso específico.
    """
    aviso = Aviso.query.get_or_404(aviso_id)
    
    # Busca todos os logs associados a este aviso, ordenando pelo mais recente
    logs = LogCienciaAviso.query.filter_by(aviso_id=aviso.id).order_by(LogCienciaAviso.data_ciencia.desc()).all()

    return render_template('avisos/log_ciencia.html', aviso=aviso, logs=logs)