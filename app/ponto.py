import os
import uuid
from datetime import datetime

from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory, jsonify)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import db
from .decorators import permission_required
from .models import Funcionario, Ponto

ponto_bp = Blueprint('ponto', __name__)

# --- Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf'}

# --- Rotas para RH ---

@ponto_bp.route('/gestao')
@login_required
@permission_required('admin_rh')
def gestao_ponto():
    """Página para o RH gerenciar e revisar pontos."""
    pontos_para_revisar = Ponto.query.filter_by(status='Em Revisão').order_by(Ponto.data_upload.asc()).all()
    return render_template('ponto/gestao.html', pontos_para_revisar=pontos_para_revisar)

@ponto_bp.route('/funcionario/<int:funcionario_id>/solicitar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def solicitar_ponto(funcionario_id):
    """Cria uma nova solicitação de ajuste de ponto para um funcionário."""
    data_ajuste_str = request.form.get('data_ajuste')
    tipo_ajuste = request.form.get('tipo_ajuste') # Pega o novo campo

    if not data_ajuste_str or not tipo_ajuste:
        flash('A data e o tipo do ajuste são obrigatórios.', 'danger')
        return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))

    data_ajuste = datetime.strptime(data_ajuste_str, '%Y-%m-%d').date()

    # Lógica de verificação alterada para incluir o tipo de ajuste
    existente = Ponto.query.filter_by(
        funcionario_id=funcionario_id, 
        data_ajuste=data_ajuste,
        tipo_ajuste=tipo_ajuste
    ).first()

    if existente:
        flash(f'Já existe uma solicitação de "{tipo_ajuste}" para o dia {data_ajuste.strftime("%d/%m/%Y")}.', 'warning')
        return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))

    nova_solicitacao = Ponto(
        funcionario_id=funcionario_id,
        data_ajuste=data_ajuste,
        tipo_ajuste=tipo_ajuste, # Salva o novo campo
        solicitante_id=current_user.id,
        status='Pendente'
    )
    db.session.add(nova_solicitacao)
    db.session.commit()
    flash(f'Solicitação de ajuste ({tipo_ajuste}) para {data_ajuste.strftime("%d/%m/%Y")} enviada!', 'success')
    return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))


# --- Rotas para Colaborador ---

@ponto_bp.route('/<int:ponto_id>/responder', methods=['POST'])
@login_required
def responder_ponto(ponto_id):
    """Processa o anexo do ponto assinado pelo colaborador."""
    ponto = Ponto.query.get_or_404(ponto_id)

    if ponto.funcionario_id != current_user.funcionario.id:
        return jsonify({'success': False, 'message': 'Acesso não autorizado.'}), 403

    if 'arquivo_assinado' not in request.files:
        return jsonify({'success': False, 'message': 'Nenhum arquivo enviado.'}), 400

    file = request.files['arquivo_assinado']
    justificativa_texto = request.form.get('justificativa', '') # Pega a justificativa

    if file.filename == '' or not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Arquivo inválido ou extensão não permitida (apenas PDF).'}), 400

    try:
        filename_seguro = secure_filename(file.filename)
        extensao = filename_seguro.rsplit('.', 1)[1]
        nome_unico = f"ponto_{ponto.funcionario_id}_{ponto.data_ajuste.strftime('%Y-%m-%d')}_{uuid.uuid4()}.{extensao}"

        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos')
        os.makedirs(upload_folder, exist_ok=True)

        file.save(os.path.join(upload_folder, nome_unico))

        ponto.path_assinado = nome_unico
        ponto.status = 'Em Revisão'
        ponto.data_upload = datetime.utcnow()
        ponto.justificativa = justificativa_texto # Salva a justificativa

        db.session.commit()
        return jsonify({'success': True, 'message': 'Ajuste de ponto enviado para revisão!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao responder ponto {ponto_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao processar o arquivo.'}), 500

@ponto_bp.route('/download_modelo')
@login_required
def download_modelo_ponto():
    """Fornece o modelo de PDF para download."""
    # O arquivo 'modelo_ponto.pdf' deve estar na pasta 'static'
    return send_from_directory(os.path.join(current_app.root_path, 'static'), 
                               'modelo_ponto.pdf', as_attachment=True)

@ponto_bp.route('/download_assinado/<filename>')
@login_required
def download_ponto_assinado(filename):
    """Permite o download do ponto assinado (para o RH)."""
    if not current_user.tem_permissao('admin_rh'):
        # Adicionar futuramente lógica para o próprio funcionário baixar
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))
        
    ponto_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos')
    return send_from_directory(ponto_folder, filename, as_attachment=True)


##  ANALISE DE PONTOS (APROVADO OU REPROVADO)

@ponto_bp.route('/<int:ponto_id>/aprovar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def aprovar_ponto(ponto_id):
    """Aprova um ajuste de ponto."""
    ponto = Ponto.query.get_or_404(ponto_id)
    
    ponto.status = 'Aprovado'
    ponto.revisor_id = current_user.id
    ponto.observacao_rh = None # Limpa observações antigas
    
    db.session.commit()
    flash(f'Ajuste de ponto de {ponto.funcionario.nome} para o dia {ponto.data_ajuste.strftime("%d/%m/%Y")} foi aprovado.', 'success')
    return redirect(url_for('ponto.gestao_ponto'))

@ponto_bp.route('/<int:ponto_id>/reprovar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def reprovar_ponto(ponto_id):
    """Reprova um ajuste de ponto e devolve a pendência ao colaborador."""
    ponto = Ponto.query.get_or_404(ponto_id)
    motivo = request.form.get('motivo_reprovacao')

    if not motivo:
        flash('O motivo da reprovação é obrigatório.', 'danger')
        return redirect(url_for('ponto.gestao_ponto'))

    # Deleta o arquivo antigo para forçar um novo envio
    if ponto.path_assinado:
        try:
            caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos', ponto.path_assinado)
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        except OSError as e:
            current_app.logger.error(f"Erro ao remover arquivo de ponto {ponto.path_assinado}: {e}")

    ponto.status = 'Pendente' # Retorna o status para Pendente
    ponto.observacao_rh = motivo # Salva o motivo da reprovação
    ponto.path_assinado = None # Limpa o caminho do arquivo
    ponto.revisor_id = current_user.id
    
    db.session.commit()
    flash(f'Ajuste de {ponto.funcionario.nome} foi reprovado e a pendência retornou ao colaborador.', 'warning')
    return redirect(url_for('ponto.gestao_ponto'))