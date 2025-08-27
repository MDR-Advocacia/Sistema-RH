import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from . import db
from .models import Denuncia, DenunciaAnexo # Importamos o novo modelo DenunciaAnexo
from .decorators import permission_required

denuncias_bp = Blueprint('denuncias', __name__)

# --- FUNÇÃO AUXILIAR PARA VERIFICAR EXTENSÕES PERMITIDAS ---
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'mp3', 'wav', 'm4a'}
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@denuncias_bp.route('/enviar', methods=['GET', 'POST'])
@login_required
def enviar_denuncia():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')
        anexos = request.files.getlist('anexos') # Pega a lista de arquivos

        if not titulo or not conteudo:
            flash('Título e conteúdo são obrigatórios.', 'danger')
            return redirect(url_for('denuncias.enviar_denuncia'))

        nova_denuncia = Denuncia(titulo=titulo, conteudo=conteudo)
        db.session.add(nova_denuncia)
        
        # --- LÓGICA DE UPLOAD DOS ANEXOS ---
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'denuncias')
        os.makedirs(upload_folder, exist_ok=True)

        for arquivo in anexos:
            if arquivo and arquivo.filename != '' and allowed_file(arquivo.filename):
                filename_seguro = secure_filename(arquivo.filename)
                extensao = filename_seguro.rsplit('.', 1)[1].lower()
                nome_unico = f"{uuid.uuid4()}.{extensao}"
                
                arquivo.save(os.path.join(upload_folder, nome_unico))

                novo_anexo = DenunciaAnexo(
                    nome_arquivo_original=filename_seguro,
                    path_armazenamento=nome_unico,
                    denuncia=nova_denuncia # Associa o anexo à denúncia
                )
                db.session.add(novo_anexo)

        db.session.commit()
        flash('Sua denúncia foi enviada com sucesso de forma anônima.', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('denuncias/enviar.html')

@denuncias_bp.route('/gestao')
@login_required
@permission_required('admin_rh')
def gestao_denuncias():
    # ... (esta função permanece a mesma)
    denuncias = Denuncia.query.order_by(Denuncia.data_envio.desc()).all()
    return render_template('denuncias/gestao.html', denuncias=denuncias)

@denuncias_bp.route('/<int:denuncia_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def ver_denuncia(denuncia_id):
    # ... (esta função permanece a mesma)
    denuncia = Denuncia.query.get_or_404(denuncia_id)
    if request.method == 'POST':
        novo_status = request.form.get('status')
        if novo_status:
            denuncia.status = novo_status
            db.session.commit()
            flash('Status da denúncia atualizado com sucesso.', 'success')
            return redirect(url_for('denuncias.gestao_denuncias'))

    return render_template('denuncias/ver_detalhes.html', denuncia=denuncia)

# --- NOVA ROTA PARA DOWNLOAD SEGURO DOS ANEXOS ---
@denuncias_bp.route('/anexo/<filename>')
@login_required
@permission_required('admin_rh')
def download_anexo(filename):
    denuncia_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'denuncias')
    return send_from_directory(denuncia_folder, filename, as_attachment=True)