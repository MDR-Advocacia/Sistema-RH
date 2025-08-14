# app/auth.py

from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app # type: ignore
from flask_login import login_user, logout_user, login_required, current_user # type: ignore
from flask_mail import Message
from . import mail
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
    
    # Verificação de usuario suspenso
    if user.funcionario and user.funcionario.status == 'Suspenso':
        flash('Este usuário está suspenso e não pode acessar o sistema.', 'danger')
        return redirect(url_for('auth.login'))

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

@auth.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        user = Usuario.query.filter_by(email=email).first()
        if user:
            # Gerar token e enviar e-mail
            token = user.get_reset_password_token()
            msg = Message(
                'Redefinição de Senha - MDRH',
                sender=current_app.config['MAIL_SENDER'],
                recipients=[user.email]
            )
            msg.body = f'''Para redefinir sua senha, visite o seguinte link:
{url_for('auth.redefinir_senha', token=token, _external=True)}

Se você não solicitou esta alteração, ignore este e-mail.
'''
            mail.send(msg)
        
        flash('Se o e-mail estiver cadastrado em nosso sistema, um link de redefinição de senha foi enviado.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/esqueci_senha.html')


@auth.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    user = Usuario.verify_reset_password_token(token)
    if not user:
        flash('O link de redefinição de senha é inválido ou expirou.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        nova_senha = request.form.get('nova_senha')
        confirmacao = request.form.get('confirmacao_senha')

        if not nova_senha or nova_senha != confirmacao:
            flash('As senhas não conferem ou estão em branco.', 'danger')
            return redirect(url_for('auth.redefinir_senha', token=token))

        user.set_password(nova_senha)
        user.senha_provisoria = False # Garante que a flag seja desativada
        db.session.commit()

        flash('Sua senha foi atualizada com sucesso! Você já pode fazer login.', 'success')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/redefinir_senha.html')