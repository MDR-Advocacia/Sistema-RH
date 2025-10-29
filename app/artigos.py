import os
import uuid
from flask import (Blueprint, render_template, request, redirect, 
                   url_for, flash, current_app, send_from_directory)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from . import db
from .models import Artigo
from .decorators import permission_required

artigos = Blueprint('artigos', __name__)

# Permissões de Admin/Gestão para este módulo
permissoes_gestao = ['admin_rh', 'admin_ti', 'supervisor']
(['admin_rh', 'admin_ti', 'depto_pessoal'])

# ===============================================
# ROTAS PÚBLICAS (Para todos os colaboradores)
# ===============================================

@artigos.route('/artigos')
@login_required
def listar():
    """(PÚBLICO) Exibe todos os artigos publicados."""
    lista_de_artigos = Artigo.query.order_by(Artigo.data_publicacao.desc()).all()
    return render_template('artigos/listar.html', artigos=lista_de_artigos)

@artigos.route('/artigos/<int:artigo_id>')
@login_required
def visualizar(artigo_id):
    """(PÚBLICO) Exibe o conteúdo de um artigo específico."""
    artigo = Artigo.query.get_or_404(artigo_id)
    return render_template('artigos/visualizar.html', artigo=artigo)

@artigos.route('/artigos/anexo/<filename>')
@login_required
def download_anexo(filename):
    """(PÚBLICO) Permite o download do anexo (PDF) do artigo."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

# ===============================================
# ROTAS DE GESTÃO (Para Admins e Supervisores)
# ===============================================

@artigos.route('/artigos/gerenciar')
@login_required
@permission_required(permissoes_gestao)
def gerenciar():
    """(GESTÃO) Painel de administração para editar e remover artigos."""
    lista_de_artigos = Artigo.query.order_by(Artigo.data_publicacao.desc()).all()
    return render_template('artigos/gerenciar.html', artigos=lista_de_artigos)

@artigos.route('/artigos/novo', methods=['GET', 'POST'])
@login_required
@permission_required(permissoes_gestao)
def criar():
    """(GESTÃO) Formulário para criar um novo artigo."""
    if request.method == 'POST':
        arquivo = request.files.get('anexo')
        novo_artigo = Artigo(
            titulo=request.form.get('titulo'),
            resumo=request.form.get('resumo'),
            conteudo=request.form.get('conteudo'),
            link_externo=request.form.get('link_externo'),
            autor_id=current_user.id
        )

        if not novo_artigo.titulo or not novo_artigo.conteudo:
            flash('Título e Conteúdo são obrigatórios.', 'danger')
            return render_template('artigos/criar.html')

        # Lógica de Upload do Anexo
        if arquivo and arquivo.filename != '':
            filename_seguro = secure_filename(arquivo.filename)
            extensao = filename_seguro.rsplit('.', 1)[-1].lower()
            nome_unico = f"artigo_{uuid.uuid4()}.{extensao}"
            
            upload_path = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_path, exist_ok=True)
            arquivo.save(os.path.join(upload_path, nome_unico))
            
            novo_artigo.path_anexo = nome_unico
            novo_artigo.nome_anexo_original = filename_seguro

        db.session.add(novo_artigo)
        db.session.commit()
        
        flash('Artigo publicado com sucesso!', 'success')
        return redirect(url_for('artigos.gerenciar'))

    return render_template('artigos/criar.html')

@artigos.route('/artigos/<int:artigo_id>/editar', methods=['GET', 'POST'])
@login_required
@permission_required(permissoes_gestao)
def editar(artigo_id):
    """(GESTÃO) Formulário para editar um artigo existente."""
    artigo = Artigo.query.get_or_404(artigo_id)

    if request.method == 'POST':
        artigo.titulo = request.form.get('titulo')
        artigo.resumo = request.form.get('resumo')
        artigo.conteudo = request.form.get('conteudo')
        artigo.link_externo = request.form.get('link_externo')
        arquivo = request.files.get('anexo')

        if not artigo.titulo or not artigo.conteudo:
            flash('Título e Conteúdo são obrigatórios.', 'danger')
            return render_template('artigos/editar.html', artigo=artigo)

        # Lógica de Upload (se um NOVO anexo for enviado)
        if arquivo and arquivo.filename != '':
            # 1. Deletar o anexo antigo
            if artigo.path_anexo:
                try:
                    caminho_antigo = os.path.join(current_app.config['UPLOAD_FOLDER'], artigo.path_anexo)
                    if os.path.exists(caminho_antigo):
                        os.remove(caminho_antigo)
                except Exception as e:
                    current_app.logger.error(f"Erro ao remover anexo antigo do artigo {artigo.id}: {e}")

            # 2. Salvar o novo anexo
            filename_seguro = secure_filename(arquivo.filename)
            extensao = filename_seguro.rsplit('.', 1)[-1].lower()
            nome_unico = f"artigo_{uuid.uuid4()}.{extensao}"
            
            upload_path = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_path, exist_ok=True)
            arquivo.save(os.path.join(upload_path, nome_unico))
            
            artigo.path_anexo = nome_unico
            artigo.nome_anexo_original = filename_seguro

        db.session.commit()
        flash('Artigo atualizado com sucesso!', 'success')
        return redirect(url_for('artigos.gerenciar'))

    # Método GET: Apenas exibe o formulário preenchido
    return render_template('artigos/editar.html', artigo=artigo)

@artigos.route('/artigos/<int:artigo_id>/remover', methods=['POST'])
@login_required
@permission_required(permissoes_gestao)
def remover(artigo_id):
    """(GESTÃO) Remove um artigo do banco de dados."""
    artigo = Artigo.query.get_or_404(artigo_id)
    titulo_artigo = artigo.titulo

    try:
        # 1. Deletar o anexo (se existir)
        if artigo.path_anexo:
            try:
                caminho_anexo = os.path.join(current_app.config['UPLOAD_FOLDER'], artigo.path_anexo)
                if os.path.exists(caminho_anexo):
                    os.remove(caminho_anexo)
            except Exception as e:
                current_app.logger.error(f"Erro ao remover anexo do artigo {artigo.id}: {e}")
        
        # 2. Deletar o artigo do banco
        db.session.delete(artigo)
        db.session.commit()
        
        flash(f'Artigo "{titulo_artigo}" removido com sucesso.', 'success')
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Erro ao remover artigo {artigo.id}: {e}")
        flash('Ocorreu um erro ao tentar remover o artigo.', 'danger')

    return redirect(url_for('artigos.gerenciar'))