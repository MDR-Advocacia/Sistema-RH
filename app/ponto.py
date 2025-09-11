# app/ponto.py

import os
import uuid
from datetime import datetime
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory, jsonify, after_this_request, send_file)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from docxtpl import DocxTemplate
from io import BytesIO
from .utils import registrar_log # <-- Importar a função de log
from .email import send_email
from . import db
from .decorators import permission_required
from .models import Funcionario, Ponto


ponto_bp = Blueprint('ponto', __name__)

# --- Função Auxiliar ---
def allowed_file(filename):
    """Verifica se a extensão do arquivo é permitida (apenas PDF)."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf'}

# --- Rotas para RH ---

@ponto_bp.route('/gestao', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def gestao_ponto():
    """Página unificada para o RH gerenciar pontos: solicitar e revisar."""
    if request.method == 'POST':
        # Lógica para SOLICITAR um novo ponto
        funcionario_id = request.form.get('funcionario_id')
        data_ajuste_str = request.form.get('data_ajuste')
        tipo_ajuste = request.form.get('tipo_ajuste')

        if not all([funcionario_id, data_ajuste_str, tipo_ajuste]):
            flash('Funcionário, data e tipo do ajuste são obrigatórios.', 'danger')
            return redirect(url_for('ponto.gestao_ponto'))

        data_ajuste = datetime.strptime(data_ajuste_str, '%Y-%m-%d').date()

        existente = Ponto.query.filter_by(
            funcionario_id=funcionario_id,
            data_ajuste=data_ajuste,
            tipo_ajuste=tipo_ajuste
        ).first()

        if existente:
            flash(f'Já existe uma solicitação de "{tipo_ajuste}" para o dia {data_ajuste.strftime("%d/%m/%Y")} para este funcionário.', 'warning')
            return redirect(url_for('ponto.gestao_ponto'))

        nova_solicitacao = Ponto(
            funcionario_id=funcionario_id,
            data_ajuste=data_ajuste,
            tipo_ajuste=tipo_ajuste,
            solicitante_id=current_user.id,
            status='Pendente'
        )
        db.session.add(nova_solicitacao)
        db.session.commit()

        # LOG
        funcionario = Funcionario.query.get(funcionario_id)
        registrar_log(f"Solicitou ajuste de ponto ({tipo_ajuste} em {data_ajuste.strftime('%d/%m/%Y')}) para '{funcionario.nome}'.")

        # --- LÓGICA DE NOTIFICAÇÃO POR E-MAIL ADICIONADA ---
        try:
            if funcionario and funcionario.usuario:
                send_email(funcionario.email,
                           f"Nova Solicitação de Ajuste de Ponto: {tipo_ajuste}",
                           'email/nova_solicitacao_ponto',
                           solicitacao=nova_solicitacao)
        except Exception as e:
            current_app.logger.error(f"Falha ao enviar e-mail de solicitação de ponto: {e}")
        # --- FIM DA LÓGICA DE NOTIFICAÇÃO ---

        flash(f'Solicitação de ajuste ({tipo_ajuste}) para {data_ajuste.strftime("%d/%m/%Y")} enviada!', 'success')
        return redirect(url_for('ponto.gestao_ponto'))

    # Se for GET, exibe a página de gestão
    pontos_para_revisar = Ponto.query.filter_by(status='Em Revisão').order_by(Ponto.data_upload.asc()).all()
    
    # Adicionamos a busca de funcionários para popular o novo formulário em lote
    funcionarios = Funcionario.query.filter_by(status='Ativo').order_by(Funcionario.nome).all()
    
    return render_template(
        'ponto/gestao.html', 
        pontos_para_revisar=pontos_para_revisar,
        funcionarios=funcionarios  # Passamos a lista para o template
    )

# SOLICITAR AJUSTE EM LOTE
@ponto_bp.route('/solicitar-ajuste-em-lote', methods=['POST'])
@login_required
@permission_required('admin_rh')
def solicitar_ajuste_em_lote():
    ids_funcionarios = request.form.getlist('funcionarios_selecionados')
    data_str = request.form.get('data_ajuste')
    tipo_ajuste = request.form.get('tipo_ajuste') # <-- MUDANÇA 1

    if not all([ids_funcionarios, data_str, tipo_ajuste]): # <-- MUDANÇA 2
        flash('É necessário selecionar funcionários, uma data e o tipo do ajuste.', 'warning')
        return redirect(url_for('ponto.gestao_ponto'))

    try:
        data_ajuste = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de data inválido.', 'danger')
        return redirect(url_for('ponto.gestao_ponto'))

    sucessos = 0
    for funcionario_id in ids_funcionarios:
        novo_ajuste = Ponto(
            funcionario_id=funcionario_id,
            data_ajuste=data_ajuste,
            tipo_ajuste=tipo_ajuste, # <-- MUDANÇA 3
            status='Pendente',
            solicitante_id=current_user.id
        )
        db.session.add(novo_ajuste)
        sucessos += 1

    db.session.commit()
    flash(f'Solicitação de ajuste de ponto ({tipo_ajuste}) enviada para {sucessos} funcionário(s) com sucesso!', 'success') # <-- MUDANÇA 4 (Opcional, melhora o feedback)

    return redirect(url_for('ponto.gestao_ponto')) 


@ponto_bp.route('/<int:ponto_id>/aprovar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def aprovar_ponto(ponto_id):
    """Aprova um ajuste de ponto."""
    ponto = Ponto.query.get_or_404(ponto_id)
    ponto.status = 'Aprovado'
    ponto.revisor_id = current_user.id
    ponto.observacao_rh = None
    db.session.commit()

    # LOG
    registrar_log(f"Aprovou o ajuste de ponto ({ponto.tipo_ajuste} de {ponto.data_ajuste.strftime('%d/%m/%Y')}) do funcionário '{ponto.funcionario.nome}'.")

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
        registrar_log(f"Reprovou a solicitação de ponto (ID: {ponto.id}) do funcionário '{ponto.funcionario.nome}'. Motivo: {motivo}")
        flash('O motivo da reprovação é obrigatório.', 'danger')
        return redirect(url_for('ponto.gestao_ponto'))

    if ponto.path_assinado:
        try:
            caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos', ponto.path_assinado)
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        except OSError as e:
            current_app.logger.error(f"Erro ao remover arquivo de ponto {ponto.path_assinado}: {e}")

    ponto.status = 'Pendente'
    ponto.observacao_rh = motivo
    ponto.path_assinado = None
    ponto.revisor_id = current_user.id
    db.session.commit()

    # LOG
    registrar_log(f"Reprovou o ajuste de ponto ({ponto.tipo_ajuste} de {ponto.data_ajuste.strftime('%d/%m/%Y')}) do funcionário '{ponto.funcionario.nome}' pelo motivo: '{motivo}'.")
    
    # --- LÓGICA DE NOTIFICAÇÃO POR E-MAIL ADICIONADA ---
    try:
        if ponto.funcionario and ponto.funcionario.usuario:
            send_email(ponto.funcionario.email,
                       f"Correção Necessária no Ajuste de Ponto",
                       'email/ponto_reprovado',
                       ponto=ponto, motivo=motivo)
    except Exception as e:
        current_app.logger.error(f"Falha ao enviar e-mail de reprovação de ponto: {e}")
    # --- FIM DA LÓGICA DE NOTIFICAÇÃO ---

    flash(f'Ajuste de {ponto.funcionario.nome} foi reprovado e a pendência retornou ao colaborador.', 'warning')
    return redirect(url_for('ponto.gestao_ponto'))

# REMOÇÃO VIA FORMULARIO
@ponto_bp.route('/<int:ponto_id>/remover', methods=['POST'])
@login_required
@permission_required('admin_rh')
def remover_ponto(ponto_id):
    """Remove uma solicitação de ajuste de ponto."""
    ponto = Ponto.query.get_or_404(ponto_id)
    funcionario_id = ponto.funcionario_id
    
    try:
        # LOG (registra antes de deletar para ter acesso aos dados)
        registrar_log(f"Removeu a solicitação de ajuste de ponto ({ponto.tipo_ajuste} de {ponto.data_ajuste.strftime('%d/%m/%Y')}) do funcionário '{ponto.funcionario.nome}'.")

        if ponto.path_assinado:
            caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos', ponto.path_assinado)
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        db.session.delete(ponto)
        db.session.commit()
        registrar_log(f"Removeu a solicitação de ponto (ID: {ponto.id}) do funcionário '{funcionario_nome}'.")
        flash('Solicitação de ajuste de ponto removida com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Erro ao remover a solicitação de ajuste.', 'danger')
        current_app.logger.error(f"Erro ao remover solicitação de ponto {ponto_id}: {e}")

    return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))

# REMOÇÃO VIA API
@ponto_bp.route('/api/ponto/<int:ponto_id>/remover', methods=['DELETE'])
@login_required
@permission_required('admin_rh')
def remover_ponto_api(ponto_id):
    """Remove uma solicitação de ajuste de ponto via API."""
    ponto = Ponto.query.get_or_404(ponto_id)
    try:
        registrar_log(f"Removeu (via API) o ajuste de ponto ({ponto.tipo_ajuste} de {ponto.data_ajuste.strftime('%d/%m/%Y')}) do funcionário '{ponto.funcionario.nome}'.")
        if ponto.path_assinado:
            caminho_arquivo = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos', ponto.path_assinado)
            if os.path.exists(caminho_arquivo):
                os.remove(caminho_arquivo)
        db.session.delete(ponto)
        db.session.commit()
        registrar_log(f"Removeu a solicitação de ponto (ID: {ponto.id}) do funcionário '{funcionario_nome}'.")
        return jsonify({'success': True, 'message': 'Ajuste de ponto removido com sucesso!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover ajuste de ponto {ponto_id} via API: {e}")
        return jsonify({'success': False, 'message': 'Erro ao remover o ajuste de ponto.'}), 500    


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
    justificativa_texto = request.form.get('justificativa', '')

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
        ponto.justificativa = justificativa_texto

        db.session.commit()
        registrar_log(f"Respondeu à solicitação de ponto (ID: {ponto.id}) com a justificativa: '{ponto.justificativa}'.")
        return jsonify({'success': True, 'message': 'Ajuste de ponto enviado para revisão!'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao responder ponto {ponto_id}: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao processar o arquivo.'}), 500

@ponto_bp.route('/<int:ponto_id>/gerar_documento')
@login_required
def gerar_e_baixar_documento(ponto_id):
    """Preenche um template DOCX com dados do ajuste e o envia para download."""
    ponto = Ponto.query.get_or_404(ponto_id)
    if ponto.funcionario_id != current_user.funcionario.id:
        flash("Acesso não autorizado.", "danger")
        return redirect(url_for('main.index'))

    try:
        template_path = os.path.join(current_app.root_path, '..', 'static', 'modelo_justificativa_ponto.docx')
        doc = DocxTemplate(template_path)

        context = {
            'nome': ponto.funcionario.nome,
            'cargo': ponto.funcionario.cargo or "N/A",
            'data_ajuste': ponto.data_ajuste.strftime('%d/%m/%Y'),
            'justificativa': request.args.get('justificativa', 'Nenhuma justificativa fornecida.')
        }

        doc.render(context)

        file_stream = BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        download_filename = f"Justificativa_{ponto.funcionario.nome.split()[0]}_{ponto.data_ajuste.strftime('%d-%m-%Y')}.docx"

        return send_file(
            file_stream,
            as_attachment=True,
            download_name=download_filename,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        current_app.logger.error(f"Erro ao gerar documento de ponto: {e}")
        flash("Ocorreu um erro ao gerar o documento. Verifique se o modelo 'modelo_justificativa_ponto.docx' existe na pasta 'static'.", "danger")
        return redirect(request.referrer or url_for('main.index'))

@ponto_bp.route('/download_assinado/<filename>')
@login_required
def download_ponto_assinado(filename):
    """Permite o download do ponto assinado (para o RH)."""
    if not current_user.tem_permissao('admin_rh'):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('main.index'))
        
    ponto_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'pontos')
    return send_from_directory(ponto_folder, filename, as_attachment=True)

@ponto_bp.route('/api/funcionario/<int:funcionario_id>/historico')
@login_required
@permission_required('admin_rh')
def historico_ponto_funcionario(funcionario_id):
    """Retorna o histórico de pontos de um funcionário em formato JSON."""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    pontos = Ponto.query.filter_by(funcionario_id=funcionario.id).order_by(Ponto.data_ajuste.desc()).all()
    
    historico = []
    for p in pontos:
        historico.append({
            'id': p.id,
            'data_ajuste': p.data_ajuste.strftime('%d/%m/%Y'),
            'tipo_ajuste': p.tipo_ajuste,
            'status': p.status,
            'path_assinado': url_for('ponto.download_ponto_assinado', filename=p.path_assinado) if p.path_assinado else None
        })
    return jsonify(historico)    

# ROTA RESTAURADA PARA FUNCIONAR NA PÁGINA DE PERFIL DO FUNCIONÁRIO
@ponto_bp.route('/funcionario/<int:funcionario_id>/solicitar', methods=['POST'])
@login_required
@permission_required('admin_rh')
def solicitar_ponto(funcionario_id):
    """Cria uma nova solicitação de ajuste de ponto para um funcionário a partir da página de perfil."""
    data_ajuste_str = request.form.get('data_ajuste')
    tipo_ajuste = request.form.get('tipo_ajuste')

    if not data_ajuste_str or not tipo_ajuste:
        flash('A data e o tipo do ajuste são obrigatórios.', 'danger')
        return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))

    data_ajuste = datetime.strptime(data_ajuste_str, '%Y-%m-%d').date()

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
        tipo_ajuste=tipo_ajuste,
        solicitante_id=current_user.id,
        status='Pendente'
    )
    db.session.add(nova_solicitacao)
    db.session.commit()

    flash(f'Solicitação de ajuste ({tipo_ajuste}) para {data_ajuste.strftime("%d/%m/%Y")} enviada!', 'success')
    return redirect(url_for('main.perfil_funcionario', funcionario_id=funcionario_id))
