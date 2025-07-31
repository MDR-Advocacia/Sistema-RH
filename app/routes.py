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
    # --- LÓGICA DA DASHBOARD ---
    # Somente administradores verão os dados agregados
    if current_user.is_authenticated and current_user.tem_permissao('admin_rh'):
        total_funcionarios = Funcionario.query.count()
        total_avisos = Aviso.query.count()
    else:
        total_funcionarios = 0
        total_avisos = 0

    return render_template('index.html', 
                           total_funcionarios=total_funcionarios, 
                           total_avisos=total_avisos)

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
    contato_emergencia_nome = request.form.get('contato_emergencia_nome')
    contato_emergencia_telefone = request.form.get('contato_emergencia_telefone')
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
        # --- ADICIONE ESTAS DUAS LINHAS ---
        contato_emergencia_nome=contato_emergencia_nome,
        contato_emergencia_telefone=contato_emergencia_telefone,
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
    termo_busca = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'nome_asc') # Padrão é nome ascendente

    query = Funcionario.query

    # Lógica de Busca
    if termo_busca:
        query = query.filter(or_(
            Funcionario.nome.ilike(f"%{termo_busca}%"),
            Funcionario.cpf.ilike(f"%{termo_busca}%"),
            Funcionario.setor.ilike(f"%{termo_busca}%")
        ))

    # Lógica de Ordenação
    if sort_by == 'nome_desc':
        query = query.order_by(Funcionario.nome.desc())
    else: # Padrão para 'nome_asc' ou qualquer outro valor
        query = query.order_by(Funcionario.nome.asc())
        
    funcionarios = query.all()
    
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
        data_nascimento_str = request.form.get('data_nascimento')
        funcionario.data_nascimento = datetime.strptime(data_nascimento_str, '%Y-%m-%d') if data_nascimento_str else None
        funcionario.contato_emergencia_nome = request.form.get('contato_emergencia_nome')
        funcionario.contato_emergencia_telefone = request.form.get('contato_emergencia_telefone')
        
        
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

## ALTERAÇÕES EM LOTE

@main.route('/api/funcionarios/editar-em-lote', methods=['POST'])
@login_required
@permission_required('admin_rh')
def editar_funcionarios_lote():
    data = request.get_json()
    ids = data.get('ids')
    novo_cargo = data.get('cargo')
    novo_setor = data.get('setor')

    if not ids:
        return jsonify({'success': False, 'message': 'Nenhum ID de funcionário fornecido.'}), 400

    # Cria um dicionário com os campos que realmente serão atualizados
    campos_para_atualizar = {}
    if novo_cargo:
        campos_para_atualizar['cargo'] = novo_cargo
    if novo_setor:
        campos_para_atualizar['setor'] = novo_setor
    
    if not campos_para_atualizar:
        return jsonify({'success': False, 'message': 'Nenhum campo para alterar foi preenchido.'}), 400

    try:
        query = Funcionario.query.filter(Funcionario.id.in_(ids))
        query.update(campos_para_atualizar, synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Funcionários atualizados com sucesso!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao editar funcionários em lote: {e}")
        return jsonify({'success': False, 'message': 'Ocorreu um erro durante a atualização.'}), 500


@main.route('/api/funcionarios/remover-em-lote', methods=['DELETE'])
@login_required
@permission_required('admin_rh')
def remover_funcionarios_lote():
    data = request.get_json()
    ids_para_remover = data.get('ids')

    if not ids_para_remover:
        return jsonify({'success': False, 'message': 'Nenhum funcionário selecionado.'}), 400

    try:
        # Apaga primeiro os usuários associados para evitar erro de chave estrangeira
        Usuario.query.filter(Usuario.funcionario_id.in_(ids_para_remover)).delete(synchronize_session=False)
        # Apaga os funcionários
        Funcionario.query.filter(Funcionario.id.in_(ids_para_remover)).delete(synchronize_session=False)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'{len(ids_para_remover)} funcionários foram removidos com sucesso.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover funcionários em lote: {e}")
        return jsonify({'success': False, 'message': 'Ocorreu um erro durante a remoção.'}), 500

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


# Em app/routes.py

@main.route('/importar_csv', methods=['POST'])
@login_required
@permission_required('admin_rh')
def importar_csv():
    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400

    arquivo = request.files['arquivo']
    if not arquivo or not arquivo.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Formato inválido. Envie um arquivo .csv.'}), 400

    try:
        # Pega a permissão padrão para novos usuários
        permissao_colaborador = Permissao.query.filter_by(nome='colaborador').first()
        if not permissao_colaborador:
            # Cria a permissão se ela não existir
            permissao_colaborador = Permissao(nome='colaborador', descricao='Permissões básicas de colaborador')
            db.session.add(permissao_colaborador)
            db.session.commit()

        arquivo_csv = TextIOWrapper(arquivo, encoding='utf-8')
        leitor = csv.DictReader(arquivo_csv)
        
        funcionarios_adicionados = 0
        for linha in leitor:
            cpf = linha.get('CPF')
            email = linha.get('E-mail')

            if not cpf or not email:
                continue # Pula linhas que não têm CPF ou Email

            # Verifica se o funcionário ou usuário já existem
            if Funcionario.query.filter_by(cpf=cpf).first() or Usuario.query.filter_by(email=email).first():
                continue

            # Cria o Funcionário
            novo_funcionario = Funcionario(
                nome=linha.get('Nome Completo', ''),
                cpf=cpf,
                email=email,
                telefone=linha.get('Telefone', ''),
                cargo=linha.get('Cargo', ''),
                setor=linha.get('Setor', ''),
                data_nascimento=datetime.strptime(linha.get('Data de Nascimento'), '%d/%m/%Y') if linha.get('Data de Nascimento') else None,
                contato_emergencia_nome=linha.get('Contato de Emergencia (Nome)', ''),
                contato_emergencia_telefone=linha.get('Contato de Emergencia (Telefone)', '')
            )
            db.session.add(novo_funcionario)
            db.session.commit() # Salva para obter o ID

            # Cria o Usuário associado com senha provisória
            novo_usuario = Usuario(
                email=email,
                funcionario_id=novo_funcionario.id,
                senha_provisoria=True
            )
            novo_usuario.set_password('Mudar@123') # Senha padrão provisória
            novo_usuario.permissoes.append(permissao_colaborador)
            db.session.add(novo_usuario)
            
            funcionarios_adicionados += 1

        db.session.commit()
        
        if funcionarios_adicionados > 0:
            return jsonify({'success': True, 'message': f'{funcionarios_adicionados} novos funcionários importados com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Nenhum funcionário novo para importar. Verifique se os CPFs ou e-mails já existem.'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao processar CSV: {e}")
        return jsonify({'success': False, 'message': f'Ocorreu um erro ao processar o arquivo. Verifique o formato.'}), 500