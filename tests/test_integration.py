# tests/test_integration.py

from datetime import datetime
from app.models import Usuario, Permissao, Funcionario, db
from flask import url_for

def test_acesso_negado_sem_permissao(app, client):
    """
    Teste de Integração: Garante que um usuário sem a permissão correta (admin_rh)
    recebe um erro 403 (Forbidden) ao tentar acessar a página de cadastro.
    """
    with app.app_context():
        # 1. Setup: Cria os objetos necessários no banco de dados de teste
        p_colaborador = Permissao(nome='colaborador')
        u = Usuario(username='teste', email='teste@example.com')
        u.set_password('123456')
        u.permissoes.append(p_colaborador)
        
        # AQUI ESTÁ A CORREÇÃO: Simulamos que o usuário já deu o consentimento.
        u.data_consentimento = datetime.utcnow()
        
        f = Funcionario(nome='Usuario Teste', cpf='111.111.111-11', email='teste@example.com', usuario=u)
        
        db.session.add_all([p_colaborador, u, f])
        db.session.commit()

        # 2. Simula o login do usuário
        with client.session_transaction() as session:
            session['_user_id'] = u.id
            session['_fresh'] = True
        
        # 3. Executa a Ação
        response = client.get('/cadastrar')
        
        # 4. Verifica o Resultado
        assert response.status_code == 403


def test_cadastro_de_novo_funcionario(app, client, mocker):
    """
    Teste de Integração: Simula o envio do formulário, verifica a resposta HTTP
    e confirma se os objetos foram realmente criados no banco de dados.
    """
    # --- INÍCIO DA CORREÇÃO ---
    # O alvo do patch foi corrigido para o local onde a função é USADA.
    mocker.patch(
        'app.routes.provisionar_usuario_ad', 
        return_value=(True, "Usuário criado com sucesso", "novo.usuario@mdr.local")
    )

    with app.app_context():
        # 1. Setup do admin (como antes)
        p_admin_rh = Permissao(nome='admin_rh')
        admin_user = Usuario(username='admin', email='admin@example.com', data_consentimento=datetime.utcnow())
        admin_user.set_password('admin123')
        admin_user.permissoes.append(p_admin_rh)
        admin_func = Funcionario(nome='Admin RH', cpf='999.999.999-99', email='admin@example.com', usuario=admin_user)
        db.session.add_all([p_admin_rh, admin_user, admin_func])
        db.session.commit()

        # Simula o login do admin
        with client.session_transaction() as session:
            session['_user_id'] = admin_user.id
            session['_fresh'] = True

    # 2. Dados do formulário
    dados_formulario = {
        'nome': 'Funcionario Novo',
        'cpf': '123.456.789-00',
        'email': 'novo@example.com',
        'username': 'novo.funcionario'
    }

    # 3. Executa a Ação
    response = client.post('/cadastrar', data=dados_formulario, follow_redirects=True)

    # 4. Verifica os Resultados
    assert response.status_code == 200
    # Verifica se a mensagem de sucesso (qualquer parte dela) está na página
    assert b'criado com sucesso' in response.data

    # 5. VERIFICAÇÃO NO BANCO DE DADOS (A PARTE MAIS IMPORTANTE)
    with app.app_context():
        # Verifica se o funcionário foi criado
        novo_func = Funcionario.query.filter_by(cpf='123.456.789-00').first()
        assert novo_func is not None
        assert novo_func.nome == 'Funcionario Novo'

        # Verifica se o usuário associado foi criado
        novo_user = Usuario.query.filter_by(username='novo.funcionario').first()
        assert novo_user is not None
        assert novo_user.email == 'novo.usuario@mdr.local' # Email retornado pelo mock do AD
        assert novo_user.funcionario_id == novo_func.id


def test_edicao_de_funcionario_com_sucesso(app, client, mocker):
    """
    Teste de Integração: Garante que um admin de RH consegue editar
    os dados de um funcionário e que a alteração é salva no banco.
    """
    # --- Verifique se este patch está correto ---
    mocker.patch('app.routes.habilitar_usuario_ad', return_value=(True, "OK"))
    
    id_funcionario_editado = None
    id_admin = None
    with app.app_context():
        # 1. Setup
        p_admin_rh = Permissao(nome='admin_rh')
        admin_user = Usuario(username='admin', email='admin@example.com', data_consentimento=datetime.utcnow())
        admin_user.set_password('admin123')
        admin_user.permissoes.append(p_admin_rh)
        admin_func = Funcionario(nome='Admin RH', cpf='999.999.999-99', email='admin@example.com', usuario=admin_user)
        
        func_para_editar = Funcionario(nome='Fulano Original', cpf='111.222.333-44', cargo='Assistente', email='fulano@teste.com')
        user_para_editar = Usuario(username='fulano.original', email='fulano.original@teste.com', funcionario=func_para_editar)
        user_para_editar.set_password('senha123')
        
        db.session.add_all([p_admin_rh, admin_user, admin_func, func_para_editar, user_para_editar])
        db.session.commit()
        
        id_funcionario_editado = func_para_editar.id
        id_admin = admin_user.id
    
    # 2. Login
    with client.session_transaction() as session:
        session['_user_id'] = id_admin
        session['_fresh'] = True

    # 3. Prepara os dados do formulário
    dados_edicao = { 'nome': 'Fulano Editado', 'cpf': '111.222.333-44', 'email': 'fulano_editado@example.com', 'cargo': 'Analista Pleno' }

    # 4. --- INÍCIO DA CORREÇÃO FINAL ---
    # Geramos a URL e fazemos o POST dentro de um contexto de requisição de teste
    with app.test_request_context():
        url_edicao = url_for('main.editar_funcionario', funcionario_id=id_funcionario_editado)
    
    response = client.post(url_edicao, data=dados_edicao, follow_redirects=True)
    # --- FIM DA CORREÇÃO FINAL ---

    # 5. Verifica os Resultados
    assert response.status_code == 200
    assert b'Dados do funcion\xc3\xa1rio atualizados com sucesso' in response.data

    # 6. Verifica no Banco de Dados
    with app.app_context():
        funcionario_atualizado = db.session.get(Funcionario, id_funcionario_editado)
        assert funcionario_atualizado.nome == 'Fulano Editado'
        assert funcionario_atualizado.cargo == 'Analista Pleno'