from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail

def send_async_email(app, msg):
    """Função para ser executada em uma thread separada, enviando o e-mail em segundo plano."""
    with app.app_context():
        mail.send(msg)

def send_email(to, subject, template, **kwargs):
    """Função principal para enviar e-mails."""
    app = current_app._get_current_object()
    msg = Message(
        subject,
        sender=app.config['MAIL_SENDER'],
        recipients=[to]
    )
    msg.body = render_template(template + '.txt', **kwargs)
    # Para e-mails mais elaborados no futuro, podemos usar msg.html
    
    # Inicia uma thread para enviar o e-mail sem travar a aplicação
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr