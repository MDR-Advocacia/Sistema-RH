from flask_login import current_user
from . import db
from .models import LogAtividade

def registrar_log(acao):
    """
    Cria e salva uma nova entrada de log no banco de dados.
    """
    try:
        # Garante que temos um usuário autenticado para associar ao log
        if current_user and current_user.is_authenticated:
            log = LogAtividade(
                acao=acao,
                usuario_id=current_user.id
            )
            db.session.add(log)
            db.session.commit()
    except Exception as e:
        # Em caso de falha no log, não queremos que a aplicação quebre.
        # Apenas registramos o erro no console do servidor.
        print(f"ERRO AO REGISTRAR LOG: {e}")
        db.session.rollback()