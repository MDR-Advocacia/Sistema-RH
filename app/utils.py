from flask_login import current_user
from . import db
from .models import LogAtividade
from unidecode import unidecode
import re

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


def normalizar_nome(nome):
    """
    Prepara um nome para comparação, removendo acentos, espaços extras
    e convertendo para minúsculas.
    """
    if not nome:
        return ""
    # Remove acentos e caracteres especiais (ex: "João" -> "Joao")
    nome_limpo = unidecode(nome)
    # Converte para minúsculas
    nome_limpo = nome_limpo.lower()
    # Remove qualquer coisa que não seja letra ou espaço
    nome_limpo = re.sub(r'[^a-z\s]', '', nome_limpo)
    # Substitui múltiplos espaços por um único espaço
    nome_limpo = re.sub(r'\s+', ' ', nome_limpo).strip()
    return nome_limpo