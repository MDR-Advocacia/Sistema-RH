from unittest.mock import MagicMock
from app.models import Funcionario

def test_provisionar_usuario_ad_gera_username_padrao(app, mocker):
    """
    Verifica se a função gera o username no formato 'nome.sobrenome' corretamente
    e remove caracteres especiais.
    """
    with app.app_context():
        mock_conn = MagicMock()
        mock_conn.result = {'result': 0}
        mocker.patch('app.ad_sync.get_ad_connection', return_value=mock_conn)
        mock_conn.entries = []

        funcionario_teste = Funcionario(nome='João da Silva', email='joao.silva@teste.com', cpf='123')
        
        from app.ad_sync import provisionar_usuario_ad
        provisionar_usuario_ad(funcionario_teste)

        args, kwargs = mock_conn.add.call_args
        atributos = kwargs.get('attributes', {})
        
        assert atributos.get('sAMAccountName') == 'joao.silva'

def test_provisionar_usuario_ad_com_nome_simples(app, mocker):
    """
    Verifica se a função lida corretamente com nomes sem sobrenome,
    gerando um username sem ponto.
    """
    with app.app_context():
        mock_conn = MagicMock()
        mock_conn.result = {'result': 0}
        mocker.patch('app.ad_sync.get_ad_connection', return_value=mock_conn)
        mock_conn.entries = []

        funcionario_teste = Funcionario(nome='Madonna', email='madonna@teste.com', cpf='456')

        from app.ad_sync import provisionar_usuario_ad
        provisionar_usuario_ad(funcionario_teste)

        args, kwargs = mock_conn.add.call_args
        atributos = kwargs.get('attributes', {})

        # --- CORREÇÃO DA ASSERÇÃO ---
        assert atributos.get('sAMAccountName') == 'madonna'

def test_provisionar_usuario_ad_falha_de_conexao(app, mocker):
    """
    Verifica se a função retorna um erro correto quando a conexão com o AD falha.
    """
    with app.app_context():
        mocker.patch('app.ad_sync.get_ad_connection', return_value=None)
        
        funcionario_teste = Funcionario(nome='Teste Falha', email='falha@teste.com', cpf='789')
        
        from app.ad_sync import provisionar_usuario_ad
        sucesso, msg, _ = provisionar_usuario_ad(funcionario_teste)
        
        assert not sucesso
        # AQUI ESTÁ A CORREÇÃO: Alinhamos a mensagem esperada com a mensagem real da função.
        assert msg == "Falha na conexão com o AD."