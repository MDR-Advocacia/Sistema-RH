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
from .models import Documento, Funcionario, RequisicaoDocumento

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
        # Esta lógica agora lida com o formulário da aba "Solicitar"
        funcionario_id = request.form.get('funcionario_id')
        tipo_documento = request.form.get('tipo_documento_solicitado')
        
        if not funcionario_id or not tipo_documento:
            flash('Funcionário e Tipo de Documento são obrigatórios.', 'danger')
            return redirect(url_for('documentos.gestao_documentos'))

        nova_requisicao = RequisicaoDocumento(
            tipo_documento=tipo_documento,
            solicitante_id=current_user.id,
            destinatario_id=funcionario_id
        )
        db.session.add(nova_requisicao)
        db.session.commit()

        # LOG
        registrar_log(f"Solicitou o documento '{tipo_documento}' para o funcionário '{funcionario.nome}'.")
        flash(f'Solicitação de "{tipo_documento}" enviada com sucesso!', 'success')
        return redirect(url_for('documentos.gestao_documentos'))

    # Para GET, carrega os documentos para revisão e renderiza a página
    documentos_para_revisar = Documento.query.filter_by(status='Pendente de Revisão').order_by(Documento.data_upload.asc()).all()
    return render_template('documentos/gestao.html', documentos_para_revisar=documentos_para_revisar)


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
    tipo_documento = request.form.get('tipo_documento')
    
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo selecionado.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    file = request.files['arquivo']

    if not all([funcionario_id, tipo_documento, file.filename]):
        flash('Funcionário, tipo de documento e arquivo são obrigatórios.', 'danger')
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
            tipo_documento=tipo_documento,
            path_armazenamento=nome_unico,
            funcionario_id=funcionario_id,
            status='Aprovado',
            revisor_id=current_user.id,
            data_revisao=datetime.utcnow()
        )
        db.session.add(novo_documento)
        db.session.commit()
        
        # LOG
        funcionario = Funcionario.query.get(funcionario_id)
        registrar_log(f"Enviou manualmente o documento '{tipo_documento}' para o funcionário '{funcionario.nome}'.")

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
            tipo_documento=requisicao.tipo_documento,
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
    documento = Documento.query.get_or_404(documento_id)
    motivo = request.form.get('motivo_reprovacao')

    if not motivo:
        flash('O motivo da reprovação é obrigatório.', 'danger')
        return redirect(url_for('documentos.gestao_documentos'))

    try:
        caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], documento.path_armazenamento)

        if documento.requisicao_id:
            requisicao = RequisicaoDocumento.query.get(documento.requisicao_id)
            if requisicao:
                requisicao.status = 'Pendente' 
                requisicao.observacao = motivo

        db.session.delete(documento)
        
        if os.path.exists(caminho_arquivo):
            os.remove(caminho_arquivo)

        db.session.commit()

        # LOG
        registrar_log(f"Reprovou o documento '{documento.tipo_documento}' do funcionário '{documento.funcionario.nome}' pelo motivo: '{motivo}'.")

        flash(f'Documento de {documento.funcionario.nome} foi reprovado e a pendência retornou ao colaborador.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash('Ocorreu um erro ao processar a reprovação.', 'danger')
        current_app.logger.error(f"Erro ao reprovar documento {documento_id}: {e}")

    return redirect(url_for('documentos.gestao_documentos'))
