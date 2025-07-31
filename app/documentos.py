# app/documentos.py

import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import uuid

from .models import Funcionario, Documento
from .decorators import permission_required
from . import db

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
    """Página principal da gestão de documentos, com busca de funcionários."""
    return render_template('documentos/gestao.html')

@documentos_bp.route('/funcionario/<int:funcionario_id>')
@login_required
@permission_required('admin_rh')
def ver_documentos_funcionario(funcionario_id):
    """Exibe os documentos de um funcionário específico."""
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    return render_template('documentos/ver_documentos.html', funcionario=funcionario)

@documentos_bp.route('/funcionario/<int:funcionario_id>/upload', methods=['POST'])
@login_required
@permission_required('admin_rh')
def upload_documento(funcionario_id):
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
        # Gera um nome de arquivo único e seguro
        filename_seguro = secure_filename(file.filename)
        extensao = filename_seguro.rsplit('.', 1)[1]
        nome_unico = f"{uuid.uuid4()}.{extensao}"
        
        # Caminho onde o arquivo será salvo
        upload_path = os.path.join(current_app.root_path, '..', UPLOAD_FOLDER)
        if not os.path.exists(upload_path):
            os.makedirs(upload_path)
            
        file.save(os.path.join(upload_path, nome_unico))

        # Salva o registro no banco de dados
        novo_documento = Documento(
            nome_arquivo=filename_seguro,
            tipo_documento=tipo_documento,
            path_armazenamento=nome_unico, # Salvamos apenas o nome único
            funcionario_id=funcionario.id
        )
        db.session.add(novo_documento)
        db.session.commit()
        
        flash('Documento enviado com sucesso!')
    else:
        flash('Extensão de arquivo não permitida.')

    return redirect(url_for('documentos.ver_documentos_funcionario', funcionario_id=funcionario.id))


@documentos_bp.route('/download/<path:filename>')
@login_required
@permission_required('admin_rh')
def download_documento(filename):
    upload_path = os.path.join(current_app.root_path, '..', UPLOAD_FOLDER)
    return send_from_directory(upload_path, filename, as_attachment=True)