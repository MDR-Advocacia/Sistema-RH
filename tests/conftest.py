import pytest
from app import create_app, db

# O escopo foi alterado para 'function'
@pytest.fixture(scope='function')
def app():
    """Cria e configura uma nova instância do app para cada teste."""
    app = create_app(config_name='testing')
    
    with app.app_context():
        db.create_all()
        
        yield app
        
        db.session.remove()
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Um cliente de teste para a aplicação."""
    return app.test_client()