# app/decorators.py

from functools import wraps
from flask import abort
from flask_login import current_user

def permission_required(permission):
    """
    Decorador que verifica se o usuário logado tem uma permissão específica.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # Se o usuário não estiver nem logado, o @login_required já o redirecionará.
                # Mas por segurança, podemos abortar aqui também.
                abort(403)
            if not current_user.tem_permissao(permission):
                # Se o usuário não tiver a permissão, ele verá um erro "Forbidden".
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator