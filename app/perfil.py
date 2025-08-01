import os
import uuid
from flask import (Blueprint, render_template, request, redirect, url_for,
                   flash, current_app, send_from_directory)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from .models import Funcionario
from . import db

perfil_bp = Blueprint('perfil', __name__)

# Configurações de Upload
FOTOS_PERFIL_FOLDER = 'fotos_perfil'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@perfil_bp.route('/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    funcionario = current_user.funcionario

    if request.method == 'POST':
        # Atualiza os dados do formulário
        funcionario.nome = request.form.get('nome')
        funcionario.apelido = request.form.get('apelido')
        funcionario.telefone = request.form.get('telefone')
        funcionario.contato_emergencia_nome = request.form.get('contato_emergencia_nome')
        funcionario.contato_emergencia_telefone = request.form.get('contato_emergencia_telefone')

        # Lógica para o upload da foto
        if 'foto_perfil' in request.files:
            file = request.files['foto_perfil']
            if file and file.filename != '' and allowed_file(file.filename):
                filename_seguro = secure_filename(file.filename)
                extensao = filename_seguro.rsplit('.', 1)[1]
                nome_unico = f"{uuid.uuid4()}.{extensao}"
                
                if funcionario.foto_perfil:
                    try:
                        os.remove(os.path.join(current_app.config['UPLOAD_FOLDER'], FOTOS_PERFIL_FOLDER, funcionario.foto_perfil))
                    except OSError:
                        pass 

                # Salva a nova foto
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], FOTOS_PERFIL_FOLDER)
                
                # --- LINHA CORRIGIDA ---
                # Garante que o diretório de upload exista
                os.makedirs(upload_path, exist_ok=True)
                
                file.save(os.path.join(upload_path, nome_unico))
                
                funcionario.foto_perfil = nome_unico

        db.session.commit()
        db.session.refresh(funcionario)
        flash('Perfil atualizado com sucesso!', 'success')
        return redirect(url_for('perfil.editar_perfil'))

    return render_template('perfil/editar_perfil.html', funcionario=funcionario)


@perfil_bp.route('/uploads/fotos_perfil/<filename>')
def uploaded_file(filename):
    """Rota para servir os arquivos de foto de perfil."""
    return send_from_directory(os.path.join(current_app.config['UPLOAD_FOLDER'], FOTOS_PERFIL_FOLDER), filename)