from functools import wraps
from flask import abort
from flask_login import current_user

def permission_required(permissions):
    """
    Decorador que verifica se o usuário logado tem uma ou mais permissões.
    Pode receber uma string (uma permissão) ou uma lista (várias permissões).
    """
    # Garante que 'permissions' seja sempre uma lista
    if not isinstance(permissions, list):
        permissions = [permissions]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(403)
            
            # Verifica se o usuário tem pelo menos UMA das permissões necessárias
            if not any(current_user.tem_permissao(p) for p in permissions):
                abort(403) # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator