# tests/test_models.py

import unittest
from app import db # <--- Adicione esta linha
from app.models import Usuario, Permissao # <--- E esta linha

class UserModelTestCase(unittest.TestCase):
    
    def test_password_setter(self):
        """Verifica se o hash da senha é gerado e não é a senha em texto plano."""
        u = Usuario()
        u.set_password('gato123')
        self.assertIsNotNone(u.password_hash)
        self.assertNotEqual(u.password_hash, 'gato123')

    def test_no_password_getter(self):
        """Verifica se a tentativa de ler a senha levanta um AttributeError."""
        u = Usuario()
        u.set_password('gato123')
        with self.assertRaises(AttributeError):
            _ = u.password

    def test_password_verification(self):
        """Verifica se a senha correta é validada e a incorreta é rejeitada."""
        u = Usuario()
        u.set_password('gato123')
        self.assertTrue(u.check_password('gato123'))
        self.assertFalse(u.check_password('cachorro456'))

    def test_password_salts_are_random(self):
        """Verifica se senhas iguais para usuários diferentes geram hashes diferentes."""
        u1 = Usuario()
        u1.set_password('gato123')
        u2 = Usuario()
        u2.set_password('gato123')
        self.assertNotEqual(u1.password_hash, u2.password_hash)

    def test_user_permission(self):
        """Verifica a lógica de atribuição e checagem de permissões."""
        # Cria instâncias "em memória" para o teste
        u = Usuario()
        p_rh = Permissao(nome='admin_rh')
        p_ti = Permissao(nome='admin_ti')
        
        # Adiciona uma permissão e verifica
        u.permissoes.append(p_rh)
        
        self.assertTrue(u.tem_permissao('admin_rh'))
        self.assertFalse(u.tem_permissao('admin_ti'))
        
        # Verifica com uma lista de permissões
        self.assertTrue(u.tem_permissao(['admin_rh', 'colaborador']))


def test_password_hashing(app):
    """
    Teste Unitário: Garante que a senha do usuário é corretamente
    hasheada e que a verificação de senha funciona.
    """
    with app.app_context():
        u = Usuario(username='susan')
        u.set_password('gato')

        assert u.password_hash is not None
        assert u.password_hash != 'gato'
        assert u.check_password('gato')
        assert not u.check_password('cachorro')

def test_usuario_possui_permissao(app):
    """
    Teste Unitário: Garante que o método 'tem_permissao'
    do modelo Usuario funciona como esperado.
    """
    with app.app_context():
        # ... (setup do teste, que já está correto) ...
        p_admin = Permissao(nome='admin')
        p_colab = Permissao(nome='colaborador')
        user_admin = Usuario(username='admin', email='admin@test.com')
        user_admin.set_password('adminpass')
        user_admin.permissoes.append(p_admin)
        user_colab = Usuario(username='colab', email='colab@test.com')
        user_colab.set_password('colabpass')
        user_colab.permissoes.append(p_colab)
        db.session.add_all([p_admin, p_colab, user_admin, user_colab])
        db.session.commit()

        # --- INÍCIO DA CORREÇÃO FINAL ---
        # Corrigido para usar o nome de método correto: 'tem_permissao'
        assert user_admin.tem_permissao('admin')
        assert not user_admin.tem_permissao('colaborador')
        assert user_colab.tem_permissao('colaborador')
        assert not user_colab.tem_permissao('admin')
        # --- FIM DA CORREÇÃO FINAL ---       