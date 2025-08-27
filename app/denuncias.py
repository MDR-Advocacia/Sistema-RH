from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from . import db
from .models import Denuncia
from .decorators import permission_required

denuncias_bp = Blueprint('denuncias', __name__)

@denuncias_bp.route('/enviar', methods=['GET', 'POST'])
@login_required
def enviar_denuncia():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        conteudo = request.form.get('conteudo')

        if not titulo or not conteudo:
            flash('Título e conteúdo são obrigatórios.', 'danger')
            return redirect(url_for('denuncias.enviar_denuncia'))

        nova_denuncia = Denuncia(titulo=titulo, conteudo=conteudo)
        db.session.add(nova_denuncia)
        db.session.commit()
        flash('Sua denúncia foi enviada com sucesso de forma anônima.', 'success')
        return redirect(url_for('main.index'))
        
    return render_template('denuncias/enviar.html')

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
        novo_status = request.form.get('status')
        if novo_status:
            denuncia.status = novo_status
            db.session.commit()
            flash('Status da denúncia atualizado com sucesso.', 'success')
            return redirect(url_for('denuncias.gestao_denuncias'))

    return render_template('denuncias/ver_detalhes.html', denuncia=denuncia)