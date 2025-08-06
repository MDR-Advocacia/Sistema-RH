import os
import uuid
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

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


@documentos_bp.route('/gestao')
@login_required
@permission_required('admin_rh')
def gestao_documentos():
    """Página unificada para gestão, consulta e revisão de documentos."""
    documentos_para_revisar = Documento.query.filter_by(status='Pendente de Revisão').order_by(Documento.data_upload.asc()).all()
    return render_template('documentos/gestao.html', documentos_para_revisar=documentos_para_revisar)


@documentos_bp.route('/funcionario/<int:funcionario_id>')
@login_required
@permission_required('admin_rh')
def ver_documentos_funcionario(funcionario_id):
    """Exibe os documentos e as requisições pendentes de um funcionário."""
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

    flash(f'Solicitação de "{tipo_documento}" enviada com sucesso!', 'success')
    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario_id))


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
        flash(f'Documento de {documento.funcionario.nome} foi reprovado e a pendência retornou ao colaborador.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash('Ocorreu um erro ao processar a reprovação.', 'danger')
        current_app.logger.error(f"Erro ao reprovar documento {documento_id}: {e}")

    return redirect(url_for('documentos.gestao_documentos'))
