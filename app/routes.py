import csv
import os
import uuid
from datetime import datetime, timedelta
from io import TextIOWrapper, StringIO

from flask import (Blueprint, request, jsonify, render_template, redirect,
                   url_for, flash, make_response, current_app, send_from_directory)
from flask_login import login_required, current_user
from sqlalchemy import or_, extract, func
from werkzeug.utils import secure_filename

from .email import send_email

from . import db, format_datetime_local
from .decorators import permission_required
from .models import (Funcionario, Permissao, Usuario, Aviso,
                     LogCienciaAviso, RequisicaoDocumento, AvisoAnexo, Ponto)

main = Blueprint('main', __name__)

# --- ROTAS PRINCIPAIS E DE DASHBOARD ---
@main.route('/')
@login_required
def index():
    dados_dashboard = {}
    usuario = current_user
    
    avisos_lidos_ids = {log.aviso_id for log in usuario.logs_ciencia}
    dados_dashboard['avisos_pendentes'] = Aviso.query.filter(
        Aviso.id.notin_(avisos_lidos_ids),
        Aviso.arquivado == False
    ).all()
    
    dados_dashboard['requisicoes_pendentes'] = RequisicaoDocumento.query.filter_by(
        destinatario_id=usuario.funcionario.id, status='Pendente'
    ).all()

    dados_dashboard['pontos_pendentes'] = Ponto.query.filter_by(
        funcionario_id=usuario.funcionario.id, status='Pendente'
    ).all()

    # --- LÓGICA DE ANIVERSARIANTES (CORRIGIDA E PARA TODOS OS USUÁRIOS) ---
    hoje = datetime.utcnow().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    
    dados_dashboard['periodo_semana'] = f"{inicio_semana.strftime('%d/%m')} - {fim_semana.strftime('%d/%m')}"
    
    aniversariantes = []
    if inicio_semana.year == fim_semana.year:
        aniversariantes = Funcionario.query.filter(
            db.func.extract('month', Funcionario.data_nascimento) == inicio_semana.month,
            db.func.extract('day', Funcionario.data_nascimento).between(inicio_semana.day, fim_semana.day)
        ).all()
    else: # Lida com a virada do ano
        dezembro = Funcionario.query.filter(
            db.func.extract('month', Funcionario.data_nascimento) == 12,
            db.func.extract('day', Funcionario.data_nascimento) >= inicio_semana.day
        ).all()
        janeiro = Funcionario.query.filter(
            db.func.extract('month', Funcionario.data_nascimento) == 1,
            db.func.extract('day', Funcionario.data_nascimento) <= fim_semana.day
        ).all()
        aniversariantes = dezembro + janeiro

    aniversariantes.sort(key=lambda f: (f.data_nascimento.month, f.data_nascimento.day))
    dados_dashboard['aniversariantes'] = aniversariantes

    # Bloco if agora cuida apenas dos dados específicos de admin
    if usuario.tem_permissao('admin_rh') or usuario.tem_permissao('admin_ti'):
        dados_dashboard['total_funcionarios'] = Funcionario.query.count()
        dados_dashboard['total_avisos'] = Aviso.query.filter_by(arquivado=False).count()

    return render_template('index.html', dados=dados_dashboard)


# --- ROTAS DE GESTÃO DE FUNCIONÁRIOS ---

# --- FUNÇÕES CORRIGIDAS ---
@main.route('/cadastrar', methods=['GET'])
@login_required
@permission_required('admin_rh')
def exibir_formulario_cadastro():
    """Apenas exibe o formulário de cadastro."""
    permissoes = Permissao.query.all()
    return render_template('cadastrar.html', permissoes=permissoes)

@main.route('/cadastrar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def processar_cadastro():
    """Processa os dados do formulário de cadastro."""
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

    if not all([nome, cpf, email, password]):
        flash('Nome, CPF, Email e Senha são obrigatórios.')
        return redirect(url_for('main.exibir_formulario_cadastro'))

    if Funcionario.query.filter_by(cpf=cpf).first() or Usuario.query.filter_by(email=email).first():
        flash('CPF ou Email já cadastrado no sistema.')
        return redirect(url_for('main.exibir_formulario_cadastro'))

    novo_funcionario = Funcionario(
        nome=nome, cpf=cpf, email=email, telefone=telefone, cargo=cargo, setor=setor,
        data_nascimento=datetime.strptime(data_nascimento_str, '%Y-%m-%d') if data_nascimento_str else None,
        contato_emergencia_nome=contato_emergencia_nome,
        contato_emergencia_telefone=contato_emergencia_telefone
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
# --- FIM DA CORREÇÃO ---


@main.route('/funcionarios')
@login_required
@permission_required('admin_rh')
def listar_funcionarios():
    termo_busca = request.args.get('q')
    sort_by = request.args.get('sort', 'nome_asc')
    # NOVO: Lógica do filtro de status
    status_filter = request.args.get('status', 'ativos') # Padrão para 'ativos'

    query = Funcionario.query

    if status_filter == 'ativos':
        query = query.filter_by(status='Ativo')
        
    elif status_filter == 'suspensos':
        query = query.filter_by(status='Suspenso')
        
    # Se for 'todos', nenhum filtro de status é aplicado

    if termo_busca:
        termo_busca = termo_busca.strip()
        query = query.filter(or_(
            Funcionario.nome.ilike(f"%{termo_busca}%"),
            Funcionario.cpf.ilike(f"%{termo_busca}%"),
            Funcionario.setor.ilike(f"%{termo_busca}%")
        ))
    if sort_by == 'nome_desc':
        query = query.order_by(Funcionario.nome.desc())
    else:
        query = query.order_by(Funcionario.nome.asc())
    funcionarios = query.all()
    return render_template('funcionarios.html', funcionarios=funcionarios)


@main.route('/funcionario/<int:funcionario_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def editar_funcionario(funcionario_id):
    # (código existente para editar funcionário)
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


@main.route('/funcionario/<int:funcionario_id>/perfil')
@login_required
@permission_required('admin_rh')
def perfil_funcionario(funcionario_id):
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    usuario = funcionario.usuario
    pendencias_list = []
    if usuario:
        avisos_lidos_ids = {log.aviso_id for log in usuario.logs_ciencia}
        avisos_pendentes = Aviso.query.filter(
            Aviso.id.notin_(avisos_lidos_ids),
            Aviso.arquivado == False
        ).all()
        for aviso in avisos_pendentes:
            pendencias_list.append({'id': f'aviso_{aviso.id}', 'descricao': f"Ciência pendente no aviso: '{aviso.titulo}'", 'status': 'Pendente'})
    
    requisicoes_pendentes = RequisicaoDocumento.query.filter_by(destinatario_id=funcionario.id, status='Pendente').all()
    for req in requisicoes_pendentes:
        pendencias_list.append({'id': f'requisicao_{req.id}', 'descricao': f"Envio pendente do documento: '{req.tipo_documento}'", 'status': 'Pendente'})
    
    # Adiciona a busca pelo histórico de pontos
    pontos = Ponto.query.filter_by(funcionario_id=funcionario.id).order_by(Ponto.data_ajuste.desc()).all()
        
    return render_template('funcionarios/perfil.html', 
                           funcionario=funcionario, 
                           pendencias=pendencias_list,
                           pontos=pontos) # Passa a variável 'pontos' para o template

# --- ROTAS DO MURAL DE AVISOS ---
# (código existente para avisos)
@main.route('/avisos')
@login_required
def listar_avisos():
    todos_avisos = Aviso.query.filter_by(arquivado=False).order_by(Aviso.data_publicacao.desc()).all()
    avisos_lidos_ids = {log.aviso_id for log in current_user.logs_ciencia}
    return render_template('avisos/listar_avisos.html', avisos=todos_avisos, avisos_lidos_ids=avisos_lidos_ids)

@main.route('/avisos/novo', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def criar_aviso():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')
        arquivos = request.files.getlist('anexos')
        if not titulo or not conteudo:
            flash('Título and conteúdo são obrigatórios.')
            return redirect(url_for('main.criar_aviso'))
        
        novo_aviso = Aviso(titulo=titulo, conteudo=conteudo, autor_id=current_user.id)
        db.session.add(novo_aviso)
        db.session.commit()
        
        for arquivo in arquivos:
            if arquivo and arquivo.filename != '':
                filename_seguro = secure_filename(arquivo.filename)
                extensao = filename_seguro.rsplit('.', 1)[1].lower()
                nome_unico = f"{uuid.uuid4()}.{extensao}"
                upload_path = current_app.config['UPLOAD_FOLDER']
                os.makedirs(upload_path, exist_ok=True)
                arquivo.save(os.path.join(upload_path, nome_unico))
                anexo = AvisoAnexo(
                    nome_arquivo_original=filename_seguro,
                    path_armazenamento=nome_unico,
                    aviso_id=novo_aviso.id
                )
                db.session.add(anexo)
        
        db.session.commit()

        # Início da Lógica de Notificação por E-mail
        try:
            # Notificar todos os funcionários ativos, exceto o autor
            destinatarios = Usuario.query.join(Usuario.funcionario).filter(
                Usuario.id != current_user.id,
                Funcionario.status == 'Ativo'
            ).all()
            
            for user in destinatarios:
                send_email(user.email,
                           f"Novo Aviso no Mural: {novo_aviso.titulo}",
                           'email/novo_aviso',
                           user=user, aviso=novo_aviso)
        except Exception as e:
            current_app.logger.error(f"Falha ao enviar e-mails de notificação de aviso: {e}")
        # Fim da Lógica de Notificação

        flash('Aviso publicado com sucesso!', 'success')
        return redirect(url_for('main.listar_avisos'))
        
    return render_template('avisos/criar_aviso.html')

@main.route('/avisos/anexo/<filename>')
@login_required
def download_anexo_aviso(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@main.route('/avisos/<int:aviso_id>/remover', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def remover_aviso(aviso_id):
    # (código existente)
    aviso = Aviso.query.get_or_404(aviso_id)
    try:
        for anexo in aviso.anexos:
            caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], anexo.path_armazenamento)
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        db.session.delete(aviso)
        db.session.commit()
        flash(f'Aviso "{aviso.titulo}" removido com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover aviso {aviso_id}: {e}")
        flash('Ocorreu um erro ao remover o aviso.', 'danger')
    return redirect(url_for('main.listar_avisos'))


@main.route('/avisos/<int:aviso_id>/ciencia', methods=['POST'])
@login_required
def dar_ciencia_aviso(aviso_id):
    # (código existente)
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
    # (código existente)
    aviso = Aviso.query.get_or_404(aviso_id)
    logs = LogCienciaAviso.query.filter_by(aviso_id=aviso.id).order_by(LogCienciaAviso.data_ciencia.desc()).all()
    usuarios_com_ciencia_ids = {log.usuario_id for log in logs}
    funcionarios_pendentes = Funcionario.query.join(Usuario).filter(Usuario.id.notin_(usuarios_com_ciencia_ids)).all()
    return render_template('avisos/log_ciencia.html', aviso=aviso, logs=logs, pendentes=funcionarios_pendentes)


# --- ROTAS DE ARQUIVAMENTO DE AVISOS ---
# (código existente para arquivamento)
@main.route('/aviso/<int:aviso_id>/arquivar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def arquivar_aviso(aviso_id):
    aviso = Aviso.query.get_or_404(aviso_id)
    aviso.arquivado = True
    db.session.commit()
    flash(f'Aviso "{aviso.titulo}" foi arquivado com sucesso.', 'success')
    return redirect(url_for('main.listar_avisos'))


@main.route('/aviso/<int:aviso_id>/desarquivar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def desarquivar_aviso(aviso_id):
    aviso = Aviso.query.get_or_404(aviso_id)
    aviso.arquivado = False
    db.session.commit()
    flash(f'Aviso "{aviso.titulo}" foi restaurado com sucesso.', 'success')
    return redirect(url_for('main.avisos_arquivados'))


@main.route('/avisos/arquivados')
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def avisos_arquivados():
    avisos_arquivados = Aviso.query.filter_by(arquivado=True).order_by(Aviso.data_publicacao.desc()).all()
    return render_template('avisos/avisos_arquivados.html', avisos=avisos_arquivados)


# --- ROTAS DE API ---
@main.route('/api/buscar_funcionarios')
@login_required
@permission_required('admin_rh')
def buscar_funcionarios():
    termo = request.args.get('q', '').strip()
    if not termo:
        return jsonify([])
    
    funcionarios = Funcionario.query.filter(
        or_(
            Funcionario.nome.ilike(f"%{termo}%"),
            Funcionario.cpf.ilike(f"%{termo}%"),
            Funcionario.setor.ilike(f"%{termo}%")
        )
    ).all()
    
    resultado = [{"id": f.id, "nome": f.nome, "cpf": f.cpf} for f in funcionarios]
    return jsonify(resultado)


@main.route('/api/funcionario/<int:funcionario_id>')
@login_required
@permission_required('admin_rh')
def detalhes_funcionario(funcionario_id):
    # (código existente)
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    usuario = funcionario.usuario
    pendencias_list = []
    if usuario:
        avisos_lidos_ids = {log.aviso_id for log in usuario.logs_ciencia}
        avisos_pendentes = Aviso.query.filter(
            Aviso.id.notin_(avisos_lidos_ids),
            Aviso.arquivado == False
        ).all()
        for aviso in avisos_pendentes:
            pendencias_list.append({'id': f'aviso_{aviso.id}', 'descricao': f"Ciência pendente no aviso: '{aviso.titulo}'", 'status': 'Pendente'})
    
    requisicoes_pendentes = RequisicaoDocumento.query.filter_by(destinatario_id=funcionario.id, status='Pendente').all()
    for req in requisicoes_pendentes:
        pendencias_list.append({'id': f'requisicao_{req.id}', 'descricao': f"Envio pendente do documento: '{req.tipo_documento}'", 'status': 'Pendente'})

    documentos_list = [{'id': doc.id, 'nome_arquivo': doc.nome_arquivo, 'tipo_documento': doc.tipo_documento, 'data_upload': format_datetime_local(doc.data_upload), 'url_download': url_for('documentos.download_documento', filename=doc.path_armazenamento)} for doc in funcionario.documentos]
    
    return jsonify({
        'id': funcionario.id, 'nome': funcionario.nome, 'cpf': funcionario.cpf, 'email': funcionario.email,
        'telefone': funcionario.telefone, 'cargo': funcionario.cargo, 'setor': funcionario.setor,
        'data_nascimento': funcionario.data_nascimento.strftime('%d/%m/%Y') if funcionario.data_nascimento else 'Não informado',
        'contato_emergencia_nome': funcionario.contato_emergencia_nome or 'Não informado',
        'contato_emergencia_telefone': funcionario.contato_emergencia_telefone or 'Não informado',
        'documentos': documentos_list, 'pendencias': pendencias_list
    })


@main.route('/api/funcionario/<int:funcionario_id>/remover', methods=['DELETE'])
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def remover_funcionario_api(funcionario_id):
    # (código existente)
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


@main.route('/api/funcionarios/remover-em-lote', methods=['DELETE'])
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def remover_funcionarios_lote():
    # (código existente)
    ids_para_remover = request.get_json().get('ids')
    if not ids_para_remover:
        return jsonify({'success': False, 'message': 'Nenhum funcionário selecionado.'}), 400
    try:
        Usuario.query.filter(Usuario.funcionario_id.in_(ids_para_remover)).delete(synchronize_session=False)
        Funcionario.query.filter(Funcionario.id.in_(ids_para_remover)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'message': f'{len(ids_para_remover)} funcionários foram removidos.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover em lote: {e}")
        return jsonify({'success': False, 'message': 'Ocorreu um erro durante a remoção.'}), 500


@main.route('/api/funcionarios/editar-em-lote', methods=['POST'])
@login_required
@permission_required('admin_rh')
def editar_funcionarios_lote():
    # (código existente)
    data = request.get_json()
    ids, novo_cargo, novo_setor = data.get('ids'), data.get('cargo'), data.get('setor')
    if not ids:
        return jsonify({'success': False, 'message': 'Nenhum ID fornecido.'}), 400
    campos_para_atualizar = {}
    if novo_cargo: campos_para_atualizar['cargo'] = novo_cargo
    if novo_setor: campos_para_atualizar['setor'] = novo_setor
    if not campos_para_atualizar:
        return jsonify({'success': False, 'message': 'Nenhum campo para alterar preenchido.'}), 400
    try:
        Funcionario.query.filter(Funcionario.id.in_(ids)).update(campos_para_atualizar, synchronize_session=False)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Funcionários atualizados com sucesso!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao editar em lote: {e}")
        return jsonify({'success': False, 'message': 'Ocorreu um erro na atualização.'}), 500


# --- ROTAS DE IMPORTAÇÃO/EXPORTAÇÃO ---
# (código existente para importação/exportação)
@main.route('/importar_csv', methods=['POST'])
@login_required
@permission_required('admin_rh')
def importar_csv():
    # (código existente)
    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400
    arquivo = request.files['arquivo']
    if not arquivo or not arquivo.filename.endswith('.csv'):
        return jsonify({'success': False, 'message': 'Formato inválido. Envie um arquivo .csv.'}), 400
    try:
        permissao_colaborador = Permissao.query.filter_by(nome='colaborador').first()
        if not permissao_colaborador:
            permissao_colaborador = Permissao(nome='colaborador', descricao='Permissões básicas')
            db.session.add(permissao_colaborador)
            db.session.commit()
        leitor = csv.DictReader(TextIOWrapper(arquivo, encoding='utf-8'))
        adicionados = 0
        for linha in leitor:
            cpf, email = linha.get('CPF'), linha.get('E-mail')
            if not (cpf and email) or Funcionario.query.filter_by(cpf=cpf).first() or Usuario.query.filter_by(email=email).first():
                continue
            novo_funcionario = Funcionario(
                nome=linha.get('Nome Completo', ''), cpf=cpf, email=email, telefone=linha.get('Telefone', ''),
                cargo=linha.get('Cargo', ''), setor=linha.get('Setor', ''),
                data_nascimento=datetime.strptime(linha.get('Data de Nascimento'), '%d/%m/%Y') if linha.get('Data de Nascimento') else None,
                contato_emergencia_nome=linha.get('Contato de Emergencia (Nome)', ''),
                contato_emergencia_telefone=linha.get('Contato de Emergencia (Telefone)', '')
            )
            db.session.add(novo_funcionario)
            db.session.commit()
            novo_usuario = Usuario(email=email, funcionario_id=novo_funcionario.id, senha_provisoria=True)
            novo_usuario.set_password('Mudar@123')
            novo_usuario.permissoes.append(permissao_colaborador)
            db.session.add(novo_usuario)
            adicionados += 1
        db.session.commit()
        if adicionados > 0:
            return jsonify({'success': True, 'message': f'{adicionados} novos funcionários importados com sucesso!'})
        else:
            return jsonify({'success': False, 'message': 'Nenhum funcionário novo para importar.'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao processar CSV: {e}")
        return jsonify({'success': False, 'message': 'Ocorreu um erro ao processar o arquivo.'}), 500


@main.route('/exportar_csv')
@login_required
@permission_required('admin_rh')
def exportar_csv():
    # (código existente)
    termo_busca = request.args.get('q', '').strip()
    query = Funcionario.query
    if termo_busca:
        query = query.filter(or_(
            Funcionario.nome.ilike(f"%{termo_busca}%"),
            Funcionario.cpf.ilike(f"%{termo_busca}%"),
            Funcionario.setor.ilike(f"%{termo_busca}%")
        ))
    funcionarios = query.all()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nome Completo', 'CPF', 'E-mail', 'Telefone', 'Cargo', 'Setor', 'Data de Nascimento', 'Contato de Emergencia (Nome)', 'Contato de Emergencia (Telefone)'])
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


## REDEFINIÇÃO DE SENHA
@main.route('/funcionario/<int:funcionario_id>/reset-password', methods=['POST'])
@login_required
@permission_required('admin_rh')
def reset_password(funcionario_id):
    """Marca a senha do usuário como provisória, forçando a alteração no próximo login."""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    if funcionario.usuario:
        funcionario.usuario.senha_provisoria = True
        db.session.commit()
        flash(f'A senha de {funcionario.nome} foi redefinida. O usuário deverá criar uma nova senha no próximo login.', 'success')
    else:
        flash('Este funcionário não possui um usuário de sistema para redefinir a senha.', 'danger')
    return redirect(url_for('main.editar_funcionario', funcionario_id=funcionario_id))

## ALTERAR STATUS DO FUNCIONARIO (ATIVO/SUSPENSO)
@main.route('/funcionario/<int:funcionario_id>/toggle-status', methods=['POST'])
@login_required
@permission_required('admin_rh')
def toggle_status(funcionario_id):
    """Alterna o status do funcionário entre Ativo e Suspenso."""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    novo_status = 'Suspenso' if funcionario.status == 'Ativo' else 'Ativo'
    funcionario.status = novo_status
    db.session.commit()
    flash(f'O status de {funcionario.nome} foi alterado para {novo_status}.', 'success')
    return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))