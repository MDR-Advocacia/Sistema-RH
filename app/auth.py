# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import Usuario
from . import db

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')

    # Busca o usuário pelo email
    user = Usuario.query.filter_by(email=email).first()

    # Verifica se o usuário existe e se a senha está correta
    if not user or not user.check_password(password):
        flash('Por favor, verifique seus dados de login e tente novamente.')
        return redirect(url_for('auth.login')) # Recarrega a página de login

    # Se tudo estiver correto, loga o usuário
    login_user(user)
    return redirect(url_for('main.index')) # Redireciona para a página principal

@auth.route('/logout')
@login_required # Garante que apenas usuários logados podem deslogar
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao_senha')

        if not nova_senha or nova_senha != confirmacao:
            flash('As senhas não conferem ou estão em branco.')
            return redirect(url_for('auth.change_password'))

        # Atualiza a senha e a flag no banco
        current_user.set_password(nova_senha)
        current_user.senha_provisoria = False
        db.session.commit()

        flash('Senha alterada com sucesso! Você pode prosseguir.')
        return redirect(url_for('main.index'))

    return render_template('auth/change_password.html')