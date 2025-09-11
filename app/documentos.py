import os
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from .email import send_email
from .utils import registrar_log  # <-- Importar a função de log
from . import db
from .decorators import permission_required
from .models import Funcionario, Documento, RequisicaoDocumento, TipoDocumento 
from app.forms import TipoDocumentoForm


documentos_bp = Blueprint('documentos', __name__)

# Configurações
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@documentos_bp.route('/gestao', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def gestao_documentos():
    """Página unificada para gestão de documentos: revisar, solicitar e consultar."""
    if request.method == 'POST':
        try:
            # Lida com o formulário da aba "Solicitar"
            funcionario_id = request.form.get('funcionario_id')
            tipo_documento = request.form.get('tipo_documento_solicitado')
            
            # Validação dos campos do formulário
            if not funcionario_id or not tipo_documento:
                flash('Erro: Funcionário e Tipo de Documento são obrigatórios.', 'danger')
                return redirect(url_for('documentos.gestao_documentos'))

            # 2. Busca o objeto funcionário no banco de dados
            funcionario = db.session.get(Funcionario, int(funcionario_id))
            if not funcionario:
                flash('Erro: Funcionário selecionado não foi encontrado no sistema.', 'danger')
                return redirect(url_for('documentos.gestao_documentos'))
            
            nova_requisicao = RequisicaoDocumento(
                tipo_documento=tipo_documento,
                solicitante_id=current_user.id,
                destinatario_id=int(funcionario_id)
            )
            db.session.add(nova_requisicao)
            db.session.commit()

            # 3. Agora a variável 'funcionario' existe e pode ser usada no log
            registrar_log(f"Solicitou o documento '{tipo_documento}' para o funcionário '{funcionario.nome}'.")
            flash(f'Solicitação de "{tipo_documento}" enviada com sucesso para {funcionario.nome}!', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Erro ao criar requisição de documento: {e}", exc_info=True)
            flash('Ocorreu um erro inesperado ao tentar criar a requisição.', 'danger')

        return redirect(url_for('documentos.gestao_documentos'))

    # Para GET, carrega os documentos para revisão e renderiza a página
    documentos_para_revisar = Documento.query.filter_by(status='Pendente de Revisão').order_by(Documento.data_upload.asc()).all()
    
    # --- ADIÇÕES AQUI ---
    # Buscamos todos os funcionários ativos para a lista de seleção
    funcionarios = Funcionario.query.filter_by(status='Ativo').order_by(Funcionario.nome).all()
    # Buscamos todos os tipos de documento para o dropdown
    tipos_documento = TipoDocumento.query.order_by(TipoDocumento.nome).all()
    # --- FIM DAS ADIÇÕES ---

    return render_template(
        'documentos/gestao.html',
        documentos_para_revisar=documentos_para_revisar,
        funcionarios=funcionarios,          # <-- Passa a lista para o template
        tipos_documento=tipos_documento   # <-- Passa a lista para o template
    )

# SOLICITAÇÃO EM LOTE
@documentos_bp.route('/solicitar-em-lote', methods=['POST'])
@login_required
@permission_required('admin_rh')
def solicitar_em_lote():
    ids_funcionarios = request.form.getlist('funcionarios_selecionados')
    tipo_documento_id = request.form.get('tipo_documento_id') # Alterado para tipo_documento_id

    if not ids_funcionarios or not tipo_documento_id:
        flash('Você precisa selecionar pelo menos um funcionário e um tipo de documento.', 'warning')
        return redirect(url_for('documentos.gestao_documentos'))

    tipo_doc = db.session.get(TipoDocumento, tipo_documento_id)
    if not tipo_doc:
        flash('Tipo de documento inválido.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    sucessos = 0
    erros = 0
    
    # --- CORREÇÃO ADICIONADA AQUI ---
    # Lista para guardar as novas requisições para enviar e-mail depois
    requisicoes_criadas = []

    for funcionario_id in ids_funcionarios:
        existe_pendencia = RequisicaoDocumento.query.filter_by(
            destinatario_id=funcionario_id,
            tipo_documento_id=tipo_documento_id,
            status='Pendente'
        ).first()

        if not existe_pendencia:
            nova_requisicao = RequisicaoDocumento(
                destinatario_id=funcionario_id,
                tipo_documento_id=tipo_documento_id,
                solicitante_id=current_user.id,
                status='Pendente'
            )
            db.session.add(nova_requisicao)
            requisicoes_criadas.append(nova_requisicao) # Adiciona à lista
            sucessos += 1
        else:
            erros += 1

    db.session.commit()

    # --- CORREÇÃO ADICIONADA AQUI ---
    # Loop para enviar e-mail para cada nova requisição criada
    for req in requisicoes_criadas:
        try:
            # O 'req.destinatario' já é o objeto funcionário por causa do relationship
            if req.destinatario and req.destinatario.email:
                 send_email(req.destinatario.email,
                           f"Nova Solicitacao de Documento: {tipo_doc.nome}",
                           'email/nova_solicitacao_documento',
                           requisicao=req,
                           destinatario=req.destinatario)
        except Exception as e:
            current_app.logger.error(f"Falha ao enviar e-mail de solicitacao em lote para funcionario {req.destinatario_id}: {e}")
    # --- FIM DA CORREÇÃO ---

    if sucessos > 0:
        flash(f'Documento "{tipo_doc.nome}" solicitado para {sucessos} funcionário(s) com sucesso!', 'success')
    if erros > 0:
        flash(f'{erros} funcionário(s) já possuíam uma pendência para este documento.', 'info')

    return redirect(url_for('documentos.gestao_documentos'))


# NOVO: API para a aba de consulta
@documentos_bp.route('/api/funcionario/<int:funcionario_id>/documentos')
@login_required
@permission_required('admin_rh')
def historico_documentos_funcionario(funcionario_id):
    """Retorna o histórico de documentos de um funcionário em formato JSON."""
    documentos = Documento.query.filter_by(funcionario_id=funcionario_id).order_by(Documento.data_upload.desc()).all()
    
    historico = []
    for doc in documentos:
        historico.append({
            'id': doc.id,
            'tipo_documento': doc.tipo_documento,
            'nome_arquivo': doc.nome_arquivo,
            'data_upload': doc.data_upload.strftime('%d/%m/%Y %H:%M'),
            'status': doc.status,
            'url_download': url_for('documentos.download_documento', filename=doc.path_armazenamento)
        })
    return jsonify(historico)


# ROTA PARA O NOVO FORMULÁRIO DE UPLOAD MANUAL NA PÁGINA DE GESTÃO
@documentos_bp.route('/upload-manual', methods=['POST'])
@login_required
@permission_required('admin_rh')
def upload_manual_documento():
    """Processa o upload de um novo documento pelo RH a partir da tela de gestão."""
    funcionario_id = request.form.get('funcionario_id')
    # --- MUDANÇA 1: Obter o ID em vez do texto ---
    tipo_documento_id = request.form.get('tipo_documento_id')
    
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    file = request.files['arquivo']

    # --- MUDANÇA 2: Validar o ID ---
    if not all([funcionario_id, tipo_documento_id, file.filename]):
        flash('Funcionário, tipo de documento e arquivo são obrigatórios.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))
    
    # --- MUDANÇA 3: Buscar o nome do tipo de documento no banco ---
    tipo_doc = db.session.get(TipoDocumento, int(tipo_documento_id))
    if not tipo_doc:
        flash('Tipo de documento inválido.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    if file and allowed_file(file.filename):
        filename_seguro = secure_filename(file.filename)
        extensao = filename_seguro.rsplit('.', 1)[1]
        nome_unico = f"{uuid.uuid4()}.{extensao}"

        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, nome_unico))

        novo_documento = Documento(
            nome_arquivo=filename_seguro,
            tipo_documento=tipo_doc.nome, # <-- MUDANÇA 4: Usar o nome do objeto
            path_armazenamento=nome_unico,
            funcionario_id=funcionario_id,
            status='Aprovado',
            revisor_id=current_user.id,
            data_revisao=datetime.utcnow()
        )
        db.session.add(novo_documento)
        db.session.commit()
        
        funcionario = db.session.get(Funcionario, int(funcionario_id))
        registrar_log(f"Enviou manualmente o documento '{tipo_doc.nome}' para o funcionário '{funcionario.nome}'.")

        flash('Documento enviado com sucesso!', 'success')
    else:
        flash('Extensão de arquivo não permitida.', 'danger')

    return redirect(url_for('documentos.gestao_documentos'))


@documentos_bp.route('/funcionario/<int:funcionario_id>')
@login_required
@permission_required('admin_rh')
def ver_documentos_funcionario(funcionario_id):
    """Exibe os documentos e as requisições pendentes de um funcionário (usado no perfil)."""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    
    requisicoes_pendentes = RequisicaoDocumento.query.filter_by(
        destinatario_id=funcionario.id, 
        status='Pendente'
    ).order_by(RequisicaoDocumento.data_requisicao.desc()).all()

    return render_template('documentos/ver_documentos.html', 
                           funcionario=funcionario, 
                           pendentes=requisicoes_pendentes)


@documentos_bp.route('/funcionario/<int:funcionario_id>/upload', methods=['POST'])
@login_required
@permission_required('admin_rh')
def upload_documento(funcionario_id):
    """Processa o upload de um novo documento pelo RH."""
    funcionario = Funcionario.query.get_or_404(funcionario_id)

    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.')
        return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario.id))

    file = request.files['arquivo']
    tipo_documento = request.form.get('tipo_documento')

    if file.filename == '' or not tipo_documento:
        flash('Nome do arquivo ou tipo de documento inválido.')
        return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario.id))

    if file and allowed_file(file.filename):
        filename_seguro = secure_filename(file.filename)
        extensao = filename_seguro.rsplit('.', 1)[1]
        nome_unico = f"{uuid.uuid4()}.{extensao}"

        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, nome_unico))

        novo_documento = Documento(
            nome_arquivo=filename_seguro,
            tipo_documento=tipo_documento,
            path_armazenamento=nome_unico,
            funcionario_id=funcionario.id,
            status='Aprovado', # Documentos enviados pelo RH já são aprovados
            revisor_id=current_user.id,
            data_revisao=datetime.utcnow()
        )
        db.session.add(novo_documento)
        db.session.commit()
        flash('Documento enviado com sucesso!')
    else:
        flash('Extensão de arquivo não permitida.')

    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario.id))


@documentos_bp.route('/download/<path:filename>')
@login_required
def download_documento(filename):
    # Futuramente, verificar se o documento pertence ao usuário logado
    if not current_user.tem_permissao('admin_rh'):
        # Adicionar lógica para permitir que o próprio funcionário baixe seus documentos
        pass
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@documentos_bp.route('/funcionario/<int:funcionario_id>/solicitar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def solicitar_documento(funcionario_id):
    """Cria uma nova requisição de documento para um funcionário."""
    tipo_documento = request.form.get('tipo_documento_solicitado')
    if not tipo_documento:
        flash('O tipo de documento é obrigatório para fazer uma solicitação.', 'danger')
        return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))

    nova_requisicao = RequisicaoDocumento(
        tipo_documento=tipo_documento,
        solicitante_id=current_user.id,
        destinatario_id=funcionario_id
    )
    db.session.add(nova_requisicao)
    db.session.commit()

    # Início da Lógica de Notificação por E-mail
    try:
        destinatario = Funcionario.query.get(funcionario_id)
        if destinatario and destinatario.usuario:
            send_email(destinatario.email,
                       f"Nova Solicitação de Documento: {tipo_documento}",
                       'email/nova_solicitacao_documento',
                       requisicao=nova_requisicao)
    except Exception as e:
        current_app.logger.error(f"Falha ao enviar e-mail de solicitação de documento: {e}")
    # Fim da Lógica de Notificação

    flash(f'Solicitação de "{tipo_documento}" enviada com sucesso!', 'success')
    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))

# ROTA   
@documentos_bp.route('/requisicao/<int:req_id>/remover', methods=['POST'])
@login_required
@permission_required('admin_rh')
def remover_requisicao(req_id):
    """Remove uma requisição de documento pendente."""
    requisicao = RequisicaoDocumento.query.get_or_404(req_id)
    funcionario_id = requisicao.destinatario_id
    
    try:
        db.session.delete(requisicao)
        db.session.commit()
        flash('Solicitação removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao remover a solicitação.', 'danger')
        current_app.logger.error(f"Erro ao remover requisição {req_id}: {e}")

    # --- LINHA CORRIGIDA ---
    # A variável correta é 'funcionario_id', que foi definida acima.
    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))

# NOVA ROTA DE API (remove o DOCUMENTO)
@documentos_bp.route('/api/documento/<int:documento_id>/remover', methods=['DELETE'])
@login_required
@permission_required('admin_rh')
def remover_documento_api(documento_id):
    """Remove um documento e seu arquivo físico via API."""
    documento = Documento.query.get_or_404(documento_id)
    try:
        registrar_log(f"Removeu (via API) o documento '{documento.tipo_documento}' ({documento.nome_arquivo}) do funcionário '{documento.funcionario.nome}'.")
        
        caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], documento.path_armazenamento)
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)
            
        db.session.delete(documento)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Documento removido com sucesso!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover documento {documento_id} via API: {e}")
        return jsonify({'success': False, 'message': 'Erro ao remover o documento.'}), 500    


@documentos_bp.route('/requisicao/<int:req_id>/responder', methods=['POST'])
@login_required
def responder_requisicao(req_id):
    """Processa o upload de um documento por um colaborador em resposta a uma requisição."""
    requisicao = RequisicaoDocumento.query.get_or_404(req_id)

    if requisicao.destinatario_id != current_user.funcionario.id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado.'}), 403

    if 'arquivo' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400
    
    file = request.files['arquivo']
    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Arquivo inválido ou extensão não permitida.'}), 400

    try:
        filename_seguro = secure_filename(file.filename)
        extensao = filename_seguro.rsplit('.', 1)[1]
        nome_unico = f"{uuid.uuid4()}.{extensao}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'])
        file.save(os.path.join(upload_path, nome_unico))

        novo_documento = Documento(
            nome_arquivo=filename_seguro,
            tipo_documento=requisicao.tipo.nome,
            path_armazenamento=nome_unico,
            funcionario_id=current_user.funcionario.id,
            requisicao_id=requisicao.id,
            status='Pendente de Revisão'
        )
        db.session.add(novo_documento)

        requisicao.status = 'Em Revisão'
        requisicao.observacao = None
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Documento enviado para revisão!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao responder requisicao {req_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao processar o arquivo.'}), 500

# --- ROTAS DE REVISÃO DE DOCUMENTOS (AGORA PARTE DA GESTÃO) ---

@documentos_bp.route('/documento/<int:documento_id>/aprovar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def aprovar_documento(documento_id):
    """Aprova um documento."""
    documento = Documento.query.get_or_404(documento_id)
    
    documento.status = 'Aprovado'
    documento.revisor_id = current_user.id
    documento.data_revisao = datetime.utcnow()
    
    if documento.requisicao_id:
        requisicao = RequisicaoDocumento.query.get(documento.requisicao_id)
        if requisicao:
            requisicao.status = 'Concluído'
            requisicao.data_conclusao = datetime.utcnow()

    db.session.commit()

    # LOG
    registrar_log(f"Aprovou o documento '{documento.tipo_documento}' do funcionário '{documento.funcionario.nome}'.")

    flash(f'Documento "{documento.tipo_documento}" de {documento.funcionario.nome} foi aprovado.', 'success')
    return redirect(url_for('documentos.gestao_documentos'))

@documentos_bp.route('/documento/<int:documento_id>/reprovar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def reprovar_documento(documento_id):
    """Reprova um documento, exclui o arquivo e devolve a pendência ao funcionário."""
    documento = db.session.get(Documento, documento_id)
    if not documento:
        flash('Documento não encontrado.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    motivo = request.form.get('motivo_reprovacao')

    if not motivo:
        flash('O motivo da reprovação é obrigatório.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    try:
        # --- ETAPA 1: Coletar todas as informações necessárias ---
        funcionario_nome = documento.funcionario.nome
        funcionario_email = documento.funcionario.email
        documento_tipo = documento.tipo_documento
        caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], documento.path_armazenamento)
        requisicao_original_id = documento.requisicao_id
        
        # --- ETAPA 2: Enviar o e-mail ANTES de qualquer alteração no banco ---
        # Esta é a correção crucial. A notificação agora acontece primeiro.
        try:
            send_email(funcionario_email,
                       f"Correção Necessária no Documento: {documento_tipo}",
                       'email/documento_reprovado',
                       nome_funcionario=funcionario_nome,
                       tipo_documento=documento_tipo,
                       motivo=motivo)
        except Exception as e:
            # Mesmo que o e-mail falhe, o log de erro é registrado, mas a operação continua.
            current_app.logger.error(f"Falha ao enviar e-mail de reprovação de documento: {e}")

        # --- ETAPA 3: Preparar e executar as alterações no banco de dados ---
        if requisicao_original_id:
            requisicao = db.session.get(RequisicaoDocumento, requisicao_original_id)
            if requisicao:
                requisicao.status = 'Pendente' 
                requisicao.observacoes_rh = motivo

        # Marcamos o documento para exclusão
        db.session.delete(documento)
        
        # Deletamos o arquivo físico
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

        # Efetivamos tudo no banco de uma só vez
        db.session.commit()

        # --- ETAPA 4: Ações Pós-Sucesso (Log e Flash) ---
        registrar_log(f"Reprovou o documento '{documento_tipo}' do funcionário '{funcionario_nome}' pelo motivo: '{motivo}'.")
        flash(f'Documento de {funcionario_nome} foi reprovado e a pendência retornou ao colaborador.', 'warning')

    except Exception as e:
        db.session.rollback() # Desfaz qualquer alteração no banco se algo der errado
        flash('Ocorreu um erro ao processar a reprovação.', 'danger')
        current_app.logger.error(f"Erro ao reprovar documento {documento_id}: {e}", exc_info=True)

    return redirect(url_for('documentos.gestao_documentos'))
# --- ROTAS PARA GERENCIAR TIPOS DE DOCUMENTO ---

@documentos_bp.route('/tipos', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def gerenciar_tipos_documento():
    """
    Página para gerenciar (CRUD) os Tipos de Documento.
    """
    form = TipoDocumentoForm()
    
    if form.validate_on_submit():
        # Lógica para adicionar um novo tipo de documento
        novo_tipo = TipoDocumento(
            nome=form.nome.data,
            descricao=form.descricao.data,
            obrigatorio_na_admissao=form.obrigatorio_na_admissao.data
        )
        db.session.add(novo_tipo)
        try:
            db.session.commit()
            registrar_log(f"Criou um novo tipo de documento: '{novo_tipo.nome}'.")
            flash('Novo tipo de documento cadastrado com sucesso!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um tipo de documento com este nome.', 'danger')
        return redirect(url_for('documentos.gerenciar_tipos_documento'))

    tipos_documento = TipoDocumento.query.order_by(TipoDocumento.nome).all()
    return render_template(
        'documentos/gerenciar_tipos.html', 
        tipos=tipos_documento, 
        form=form
    )

@documentos_bp.route('/tipos/<int:id>/editar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def editar_tipo_documento(id):
    """
    Rota para editar um Tipo de Documento existente.
    """
    tipo_doc = db.session.get(TipoDocumento, id)
    if not tipo_doc:
        flash('Tipo de documento não encontrado.', 'danger')
        return redirect(url_for('documentos.gerenciar_tipos_documento'))
    
    form = TipoDocumentoForm(request.form) # Carrega os dados do POST
    
    if form.validate():
        tipo_doc.nome = form.nome.data
        tipo_doc.descricao = form.descricao.data
        tipo_doc.obrigatorio_na_admissao = form.obrigatorio_na_admissao.data
        try:
            db.session.commit()
            registrar_log(f"Editou o tipo de documento ID {id} para: '{tipo_doc.nome}'.")
            flash('Tipo de documento atualizado com sucesso!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Erro: Já existe um tipo de documento com este nome.', 'danger')
    else:
        # Se a validação falhar, exibe os erros.
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Erro no campo '{getattr(form, field).label.text}': {error}", 'danger')

    return redirect(url_for('documentos.gerenciar_tipos_documento'))


@documentos_bp.route('/tipos/<int:id>/deletar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def deletar_tipo_documento(id):
    """
    Rota para deletar um Tipo de Documento.
    """
    tipo_doc = db.session.get(TipoDocumento, id)
    if tipo_doc:
        if tipo_doc.requisicoes:
            flash('Não é possível excluir este tipo de documento, pois ele já está associado a requisições existentes.', 'danger')
        else:
            registrar_log(f"Deletou o tipo de documento: '{tipo_doc.nome}' (ID: {id}).")
            db.session.delete(tipo_doc)
            db.session.commit()
            flash('Tipo de documento excluído com sucesso!', 'success')
    else:
        flash('Tipo de documento não encontrado.', 'danger')
        
    return redirect(url_for('documentos.gerenciar_tipos_documento'))