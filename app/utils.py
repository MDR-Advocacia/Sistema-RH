from flask import current_app
from flask_login import current_user
from datetime import datetime
from . import db
from .models import LogAtividade
from unidecode import unidecode
import re

def registrar_log(acao, usuario_id=None):
    """
    Registra uma ação na tabela de logs.
    O usuario_id é opcional; se não for passado, tenta pegar do current_user (se possível) ou deixa nulo.
    """
    try:
        # Se não passou ID, tenta pegar do usuário logado (se estiver num contexto de request)
        if usuario_id is None:
            from flask_login import current_user
            if current_user and current_user.is_authenticated:
                usuario_id = current_user.id
        
        if not usuario_id:
            # Se ainda assim não tiver ID (ex: log de sistema), não salva ou salva com ID de sistema se tiver
            current_app.logger.warning(f"Tentativa de log sem usuário: {acao}")
            return

        novo_log = LogAtividade(
            acao=acao,
            usuario_id=usuario_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(novo_log)
        db.session.commit()
    except Exception as e:
        # Falha silenciosa no log para não parar a aplicação
        current_app.logger.error(f"Erro ao salvar log de atividade: {e}")


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