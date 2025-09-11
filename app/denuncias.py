import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from flask_login import login_required
from werkzeug.utils import secure_filename
from . import db
from .models import Denuncia, DenunciaAnexo, Usuario, Permissao
from .email import send_email
from .decorators import permission_required

denuncias_bp = Blueprint('denuncias', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'mp3', 'wav', 'm4a'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ROTA UNIFICADA PARA O CANAL DE DENÚNCIAS
@denuncias_bp.route('/', methods=['GET', 'POST'])
@login_required
def canal():
    if request.method == 'POST':
        form_name = request.form.get('form_name')

        # Lógica para o formulário de ENVIO
        if form_name == 'enviar':
            categoria = request.form.get('categoria')
            titulo = request.form.get('titulo')
            conteudo = request.form.get('conteudo')
            anexos = request.files.getlist('anexos')

            if not titulo or not conteudo or not categoria:
                flash('Categoria, título e conteúdo são obrigatórios.', 'danger')
                return redirect(url_for('denuncias.canal'))

            protocolo = None
            while not protocolo:
                novo_protocolo = f'MDRH-{uuid.uuid4().hex[:6].upper()}'
                if not Denuncia.query.filter_by(protocolo=novo_protocolo).first():
                    protocolo = novo_protocolo
            
            nova_denuncia = Denuncia(titulo=titulo, conteudo=conteudo, categoria=categoria, protocolo=protocolo)
            db.session.add(nova_denuncia)
            
            upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'denuncias')
            os.makedirs(upload_folder, exist_ok=True)

            for arquivo in anexos:
                if arquivo and arquivo.filename != '' and allowed_file(arquivo.filename):
                    filename_seguro = secure_filename(arquivo.filename)
                    extensao = filename_seguro.rsplit('.', 1)[1].lower()
                    nome_unico = f"{uuid.uuid4()}.{extensao}"
                    arquivo.save(os.path.join(upload_folder, nome_unico))
                    novo_anexo = DenunciaAnexo(nome_arquivo_original=filename_seguro, path_armazenamento=nome_unico, denuncia=nova_denuncia)
                    db.session.add(novo_anexo)

            db.session.commit()

            # --- LÓGICA DE NOTIFICAÇÃO CORRIGIDA ---
            try:
                # 1. Encontra todos os usuários com a permissão 'admin_rh'
                admins_rh = Usuario.query.join(Usuario.permissoes).filter(Permissao.nome == 'admin_rh').all()
                
                if admins_rh:
                    emails_enviados = 0
                    for admin_user in admins_rh:
                        # 2. Acessa o perfil de funcionário vinculado ao usuário
                        if admin_user.funcionario and admin_user.funcionario.email:
                            # 3. Usa o e-mail do FUNCIONÁRIO como destinatário
                            send_email(
                                to=admin_user.funcionario.email,
                                subject="Nova Denúncia Anônima Registrada",
                                template='email/nova_denuncia',
                                denuncia=nova_denuncia
                            )
                            emails_enviados += 1
                    current_app.logger.info(f"Notificação de nova denúncia (Protocolo: {nova_denuncia.protocolo}) enviada para {emails_enviados} admin(s) de RH.")
            except Exception as e:
                current_app.logger.error(f"Falha ao enviar e-mail de notificação de nova denúncia: {e}")
            # --- FIM DA CORREÇÃO ---

            return redirect(url_for('denuncias.envio_sucesso', protocolo=protocolo))
        
        # Lógica para o formulário de CONSULTA
        elif form_name == 'consultar':
            protocolo = request.form.get('protocolo')
            if not protocolo:
                flash('Por favor, insira um número de protocolo.', 'warning')
                return redirect(url_for('denuncias.canal'))

            denuncia = Denuncia.query.filter_by(protocolo=protocolo.strip().upper()).first()
            if not denuncia:
                flash('Protocolo não encontrado. Verifique o número e tente novamente.', 'danger')
                return redirect(url_for('denuncias.canal'))
            
            return render_template('denuncias/resultado_consulta.html', denuncia=denuncia)

    # Se a requisição for GET, apenas renderiza a página principal do canal
    return render_template('denuncias/canal.html')


@denuncias_bp.route('/enviada/<protocolo>')
@login_required
def envio_sucesso(protocolo):
    return render_template('denuncias/sucesso.html', protocolo=protocolo)


@denuncias_bp.route('/gestao')
@login_required
@permission_required('admin_rh')
def gestao_denuncias():
    denuncias = Denuncia.query.order_by(Denuncia.data_envio.desc()).all()
    return render_template('denuncias/gestao.html', denuncias=denuncias)


@denuncias_bp.route('/<int:denuncia_id>', methods=['GET', 'POST'])
@login_required
@permission_required('admin_rh')
def ver_denuncia(denuncia_id):
    denuncia = Denuncia.query.get_or_404(denuncia_id)
    if request.method == 'POST':
        denuncia.status = request.form.get('status')
        denuncia.feedback_rh = request.form.get('feedback_rh') # Captura o novo campo
        db.session.commit()
        flash('Status e feedback da denúncia atualizados com sucesso.', 'success')
        return redirect(url_for('denuncias.gestao_denuncias'))

    return render_template('denuncias/ver_detalhes.html', denuncia=denuncia)

@denuncias_bp.route('/anexo/<filename>')
@login_required
@permission_required('admin_rh')
def download_anexo(filename):
    denuncia_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'denuncias')
    return send_from_directory(denuncia_folder, filename, as_attachment=True)