# app/cadastros_gerais.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from . import db
from .models import Cargo, Setor
from .decorators import permission_required

cadastros_bp = Blueprint('cadastros', __name__)

# --- ROTAS PARA CARGOS ---
@cadastros_bp.route('/cargos', methods=['GET', 'POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal', 'admin_ti'])
def gerenciar_cargos():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        if nome:
            novo_cargo = Cargo(nome=nome, descricao=descricao)
            db.session.add(novo_cargo)
            db.session.commit()
            flash('Cargo adicionado com sucesso!', 'success')
        return redirect(url_for('cadastros.gerenciar_cargos'))

    cargos = Cargo.query.order_by(Cargo.nome).all()
    return render_template('cadastros_gerais/gerenciar.html', title='Cargos', items=cargos, endpoint='cadastros.gerenciar_cargos')

# --- ROTAS PARA SETORES ---
@cadastros_bp.route('/setores', methods=['GET', 'POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal', 'admin_ti'])
def gerenciar_setores():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        if nome:
            novo_setor = Setor(nome=nome, descricao=descricao)
            db.session.add(novo_setor)
            db.session.commit()
            flash('Setor adicionado com sucesso!', 'success')
        return redirect(url_for('cadastros.gerenciar_setores'))

    setores = Setor.query.order_by(Setor.nome).all()
    return render_template('cadastros_gerais/gerenciar.html', title='Setores', items=setores, endpoint='cadastros.gerenciar_setores')