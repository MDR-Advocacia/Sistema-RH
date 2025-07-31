import csv
import json
import os
from sqlalchemy import or_
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, make_response, current_app
from .models import Funcionario, Sistema, Permissao, Usuario, Aviso, LogCienciaAviso
from io import TextIOWrapper, StringIO
from . import db
from flask_login import login_required, current_user
from .decorators import permission_required

main = Blueprint('main', __name__)

# --- ROTAS PRINCIPAIS E DE CADASTRO ---

@main.route('/')
@login_required
def index():
    return render_template('index.html')

@main.route('/cadastrar', methods=['GET'])
@login_required
@permission_required('admin_rh')
def exibir_formulario_cadastro():
    permissoes = Permissao.query.all()
    return render_template('cadastrar.html', permissoes=permissoes)

@main.route('/cadastrar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def processar_cadastro():
    nome = request.form.get('nome')
    cpf = request.form.get('cpf')
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    cargo = request.form.get('cargo')
    setor = request.form.get('setor')
    data_nascimento_str = request.form.get('data_nascimento')
    password = request.form.get('password')
    permissoes_selecionadas_ids = request.form.getlist('permissoes')

    if not nome or not cpf or not email or not password:
        flash('Nome, CPF, Email e Senha são obrigatórios.')
        return redirect(url_for('main.exibir_formulario_cadastro'))

    if Funcionario.query.filter_by(cpf=cpf).first() or Usuario.query.filter_by(email=email).first():
        flash('CPF ou Email já cadastrado no sistema.')
        return redirect(url_for('main.exibir_formulario_cadastro'))

    novo_funcionario = Funcionario(
        nome=nome, cpf=cpf, email=email, telefone=telefone, cargo=cargo, setor=setor,
        data_nascimento=datetime.strptime(data_nascimento_str, '%Y-%m-%d') if data_nascimento_str else None
    )
    db.session.add(novo_funcionario)
    db.session.commit()

    novo_usuario = Usuario(email=email, funcionario_id=novo_funcionario.id)
    novo_usuario.set_password(password)
    
    if permissoes_selecionadas_ids:
        permissoes_a_adicionar = Permissao.query.filter(Permissao.id.in_(permissoes_selecionadas_ids)).all()
        novo_usuario.permissoes = permissoes_a_adicionar

    db.session.add(novo_usuario)
    db.session.commit()

    flash(f'Funcionário {nome} e seu usuário de acesso foram criados com sucesso!')
    return redirect(url_for('main.listar_funcionarios'))

# --- ROTAS DE GESTÃO DE FUNCIONÁRIOS ---

@main.route('/funcionarios')
@login_required
@permission_required('admin_rh')
def listar_funcionarios():
    funcionarios = Funcionario.query.all()
    # A lógica de busca pode ser adicionada aqui se necessário
    return render_template('funcionarios.html', funcionarios=funcionarios)

@main.route('/funcionario/<int:funcionario_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def editar_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    usuario = funcionario.usuario
    permissoes = Permissao.query.all()

    if request.method == 'POST':
        funcionario.nome = request.form.get('nome')
        funcionario.cpf = request.form.get('cpf')
        funcionario.telefone = request.form.get('telefone')
        funcionario.cargo = request.form.get('cargo')
        funcionario.setor = request.form.get('setor')
        
        if usuario:
            permissoes_selecionadas_ids = request.form.getlist('permissoes')
            permissoes_a_adicionar = Permissao.query.filter(Permissao.id.in_(permissoes_selecionadas_ids)).all()
            usuario.permissoes = permissoes_a_adicionar

        db.session.commit()
        flash(f'Dados de {funcionario.nome} atualizados com sucesso!')
        return redirect(url_for('main.listar_funcionarios'))

    permissoes_usuario_ids = {p.id for p in usuario.permissoes} if usuario else set()
    return render_template('funcionarios/editar.html', 
                           funcionario=funcionario, 
                           permissoes=permissoes, 
                           permissoes_usuario_ids=permissoes_usuario_ids)

# --- ROTAS DO MURAL DE AVISOS ---

@main.route('/avisos')
@login_required
def listar_avisos():
    todos_avisos = Aviso.query.order_by(Aviso.data_publicacao.desc()).all()
    avisos_lidos_ids = {log.aviso_id for log in current_user.logs_ciencia}
    return render_template('avisos/listar_avisos.html', avisos=todos_avisos, avisos_lidos_ids=avisos_lidos_ids)

@main.route('/avisos/novo', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def criar_aviso():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')
        if not titulo or not conteudo:
            flash('Título e conteúdo são obrigatórios.')
            return redirect(url_for('main.criar_aviso'))
        novo_aviso = Aviso(titulo=titulo, conteudo=conteudo, autor_id=current_user.id)
        db.session.add(novo_aviso)
        db.session.commit()
        flash('Aviso publicado com sucesso!')
        return redirect(url_for('main.listar_avisos'))
    return render_template('avisos/criar_aviso.html')

@main.route('/avisos/<int:aviso_id>/ciencia', methods=['POST'])
@login_required
def dar_ciencia_aviso(aviso_id):
    aviso = Aviso.query.get_or_404(aviso_id)
    ja_deu_ciencia = LogCienciaAviso.query.filter_by(usuario_id=current_user.id, aviso_id=aviso.id).first()
    if not ja_deu_ciencia:
        log = LogCienciaAviso(usuario_id=current_user.id, aviso_id=aviso.id)
        db.session.add(log)
        db.session.commit()
        flash(f'Ciência registrada para o aviso "{aviso.titulo}".')
    return redirect(url_for('main.listar_avisos'))

@main.route('/aviso/<int:aviso_id>/logs')
@login_required
@permission_required('admin_rh')
def ver_logs_ciencia(aviso_id):
    aviso = Aviso.query.get_or_404(aviso_id)
    logs = LogCienciaAviso.query.filter_by(aviso_id=aviso.id).order_by(LogCienciaAviso.data_ciencia.desc()).all()
    usuarios_com_ciencia_ids = {log.usuario_id for log in logs}
    funcionarios_pendentes = Funcionario.query.join(Usuario).filter(Usuario.id.notin_(usuarios_com_ciencia_ids)).all()
    return render_template('avisos/log_ciencia.html', aviso=aviso, logs=logs, pendentes=funcionarios_pendentes)


# --- ROTAS DE API (para JavaScript) ---

@main.route('/api/buscar_funcionarios')
@login_required
@permission_required('admin_rh')
def buscar_funcionarios():
    termo = request.args.get('q', '').strip().lower()
    if not termo:
        return jsonify([])
    funcionarios = Funcionario.query.filter(or_(Funcionario.nome.ilike(f"%{termo}%"), Funcionario.cpf.ilike(f"%{termo}%"))).all()
    resultado = [{
        "id": f.id, "nome": f.nome, "cpf": f.cpf, "email": f.email, "telefone": f.telefone,
        "cargo": f.cargo, "setor": f.setor,
        "data_nascimento": f.data_nascimento.strftime("%Y-%m-%d") if f.data_nascimento else "",
        "contato_emergencia_nome": f.contato_emergencia_nome,
        "contato_emergencia_telefone": f.contato_emergencia_telefone
    } for f in funcionarios]
    return jsonify(resultado)

@main.route('/api/funcionario/<int:funcionario_id>')
@login_required
@permission_required('admin_rh')
def detalhes_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    documentos_list = [{
        'id': doc.id, 'nome_arquivo': doc.nome_arquivo, 'tipo_documento': doc.tipo_documento,
        'data_upload': doc.data_upload.strftime('%d/%m/%Y %H:%M'),
        'url_download': url_for('documentos.download_documento', filename=doc.path_armazenamento)
    } for doc in funcionario.documentos]
    pendencias = [
        {'id': 1, 'descricao': 'Ajuste no controle de ponto de Junho/2025', 'status': 'Pendente'},
        {'id': 2, 'descricao': 'Assinar termo de confidencialidade', 'status': 'Pendente'}
    ]
    funcionario_data = {
        'id': funcionario.id, 'nome': funcionario.nome, 'cpf': funcionario.cpf, 'email': funcionario.email,
        'telefone': funcionario.telefone, 'cargo': funcionario.cargo, 'setor': funcionario.setor,
        'data_nascimento': funcionario.data_nascimento.strftime('%d/%m/%Y') if funcionario.data_nascimento else 'Não informado',
        'contato_emergencia_nome': funcionario.contato_emergencia_nome or 'Não informado',
        'contato_emergencia_telefone': funcionario.contato_emergencia_telefone or 'Não informado',
        'documentos': documentos_list, 'pendencias': pendencias
    }
    return jsonify(funcionario_data)

@main.route('/api/funcionario/<int:funcionario_id>/remover', methods=['DELETE'])
@login_required
@permission_required('admin_rh')
def remover_funcionario_api(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    try:
        if funcionario.usuario:
            db.session.delete(funcionario.usuario)
        db.session.delete(funcionario)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Funcionário {funcionario.nome} removido com sucesso.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover funcionário {funcionario_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro ao remover o funcionário.'}), 500

# --- ROTAS ANTIGAS DE CSV (mantidas por enquanto) ---

@main.route('/exportar_csv')
def exportar_csv():
    # ... (código existente)
    pass # Mantido para não quebrar, mas pode ser refatorado