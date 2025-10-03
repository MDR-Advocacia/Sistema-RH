# app/cadastros_gerais.py

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from . import db
from .models import Cargo, Setor
from .decorators import permission_required
from .utils import registrar_log

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
            # Verifica se já existe um cargo com o mesmo nome
            if Cargo.query.filter(Cargo.nome.ilike(nome)).first():
                flash('Já existe um cargo com este nome.', 'danger')
            else:
                novo_cargo = Cargo(nome=nome, descricao=descricao)
                db.session.add(novo_cargo)
                db.session.commit()
                registrar_log(f"Criou o cargo: '{nome}'")
                flash('Cargo adicionado com sucesso!', 'success')
        return redirect(url_for('cadastros.gerenciar_cargos'))

    cargos = Cargo.query.order_by(Cargo.nome).all()
    return render_template('cadastros_gerais/gerenciar.html', title='Cargos', items=cargos, endpoint_add='cadastros.gerenciar_cargos', endpoint_edit='cadastros.editar_cargo', endpoint_delete='cadastros.deletar_cargo')

@cadastros_bp.route('/cargos/<int:id>/editar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal', 'admin_ti'])
def editar_cargo(id):
    cargo = db.session.get(Cargo, id)
    if not cargo:
        flash('Cargo não encontrado.', 'danger')
        return redirect(url_for('cadastros.gerenciar_cargos'))
    
    nome = request.form.get('nome')
    descricao = request.form.get('descricao')

    if nome:
        # Verifica se o novo nome já existe em outro cargo
        outro_cargo = Cargo.query.filter(Cargo.nome.ilike(nome), Cargo.id != id).first()
        if outro_cargo:
            flash('Já existe outro cargo com este nome.', 'danger')
        else:
            log_msg = f"Editou o cargo ID {id}. De '{cargo.nome}' para '{nome}'."
            cargo.nome = nome
            cargo.descricao = descricao
            db.session.commit()
            registrar_log(log_msg)
            flash('Cargo atualizado com sucesso!', 'success')
            
    return redirect(url_for('cadastros.gerenciar_cargos'))

@cadastros_bp.route('/cargos/<int:id>/deletar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'admin_ti']) # Apenas admins podem deletar
def deletar_cargo(id):
    cargo = db.session.get(Cargo, id)
    if not cargo:
        flash('Cargo não encontrado.', 'danger')
        return redirect(url_for('cadastros.gerenciar_cargos'))

    if cargo.funcionarios:
        flash('Não é possível excluir este cargo, pois ele está associado a funcionários.', 'danger')
        return redirect(url_for('cadastros.gerenciar_cargos'))
        
    log_msg = f"Deletou o cargo: '{cargo.nome}' (ID: {id})."
    db.session.delete(cargo)
    db.session.commit()
    registrar_log(log_msg)
    flash('Cargo excluído com sucesso!', 'success')
    return redirect(url_for('cadastros.gerenciar_cargos'))


# --- ROTAS PARA SETORES ---
@cadastros_bp.route('/setores', methods=['GET', 'POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal', 'admin_ti'])
def gerenciar_setores():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        if nome:
            if Setor.query.filter(Setor.nome.ilike(nome)).first():
                flash('Já existe um setor com este nome.', 'danger')
            else:
                novo_setor = Setor(nome=nome, descricao=descricao)
                db.session.add(novo_setor)
                db.session.commit()
                registrar_log(f"Criou o setor: '{nome}'")
                flash('Setor adicionado com sucesso!', 'success')
        return redirect(url_for('cadastros.gerenciar_setores'))

    setores = Setor.query.order_by(Setor.nome).all()
    return render_template('cadastros_gerais/gerenciar.html', title='Setores', items=setores, endpoint_add='cadastros.gerenciar_setores', endpoint_edit='cadastros.editar_setor', endpoint_delete='cadastros.deletar_setor')

@cadastros_bp.route('/setores/<int:id>/editar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'depto_pessoal', 'admin_ti'])
def editar_setor(id):
    setor = db.session.get(Setor, id)
    if not setor:
        flash('Setor não encontrado.', 'danger')
        return redirect(url_for('cadastros.gerenciar_setores'))

    nome = request.form.get('nome')
    descricao = request.form.get('descricao')

    if nome:
        outro_setor = Setor.query.filter(Setor.nome.ilike(nome), Setor.id != id).first()
        if outro_setor:
            flash('Já existe outro setor com este nome.', 'danger')
        else:
            log_msg = f"Editou o setor ID {id}. De '{setor.nome}' para '{nome}'."
            setor.nome = nome
            setor.descricao = descricao
            db.session.commit()
            registrar_log(log_msg)
            flash('Setor atualizado com sucesso!', 'success')

    return redirect(url_for('cadastros.gerenciar_setores'))

@cadastros_bp.route('/setores/<int:id>/deletar', methods=['POST'])
@login_required
@permission_required(['admin_rh', 'admin_ti'])
def deletar_setor(id):
    setor = db.session.get(Setor, id)
    if not setor:
        flash('Setor não encontrado.', 'danger')
        return redirect(url_for('cadastros.gerenciar_setores'))

    if setor.funcionarios:
        flash('Não é possível excluir este setor, pois ele está associado a funcionários.', 'danger')
        return redirect(url_for('cadastros.gerenciar_setores'))

    log_msg = f"Deletou o setor: '{setor.nome}' (ID: {id})."
    db.session.delete(setor)
    db.session.commit()
    registrar_log(log_msg)
    flash('Setor excluído com sucesso!', 'success')
    return redirect(url_for('cadastros.gerenciar_setores'))