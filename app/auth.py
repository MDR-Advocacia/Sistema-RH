# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
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