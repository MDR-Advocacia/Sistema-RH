from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

# --- Tabelas de Associação (para relações Muitos-para-Muitos) ---

# Tabela que conecta Usuarios a Permissoes
permissoes_usuarios = db.Table('permissoes_usuarios',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('permissao_id', db.Integer, db.ForeignKey('permissao.id'), primary_key=True)
)

# Tabela que conecta Funcionarios a Sistemas (Benefícios, Acessos, etc.)
funcionario_sistemas = db.Table('funcionario_sistemas',
    db.Column('funcionario_id', db.Integer, db.ForeignKey('funcionario.id'), primary_key=True),
    db.Column('sistema_id', db.Integer, db.ForeignKey('sistema.id'), primary_key=True),
    db.Column('status', db.String(50), default='Ativo'), # Ex: 'Ativo', 'Inativo', 'Pendente'
    db.Column('observacao', db.String(255)) # Ex: Login do usuário, detalhes do plano, etc.
)

# --- Modelos Principais ---

class Usuario(db.Model, UserMixin):
    """
    Representa um usuário que pode logar no sistema.
    Normalmente, um funcionário terá uma conta de usuário associada.
    """
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), unique=True) # Um usuário por funcionário
    senha_provisoria = db.Column(db.Boolean, default=True, nullable=False) # <-- ADICIONE ESTA LINHA

    # Relações
    funcionario = db.relationship('Funcionario', backref=db.backref('usuario', uselist=False))
    permissoes = db.relationship('Permissao', secondary=permissoes_usuarios, lazy='subquery',
                                 backref=db.backref('usuarios', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def tem_permissao(self, nome_permissao):
        return any(p.nome == nome_permissao for p in self.permissoes)

class Permissao(db.Model):
    """
    Define as permissões granulares do sistema.
    Ex: 'admin_rh', 'ver_holerite_equipe', 'criar_aviso', 'admin_ti'
    """
    __tablename__ = 'permissao'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(255))

class Funcionario(db.Model):
    """
    Armazena os dados cadastrais do colaborador.
    """
    __tablename__ = 'funcionario'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20))
    cargo = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    data_nascimento = db.Column(db.Date)
    contato_emergencia_nome = db.Column(db.String(120))
    contato_emergencia_telefone = db.Column(db.String(20))
    foto_perfil = db.Column(db.String(255), nullable=True) # FOTO DE PERFIL

    # Relações
    sistemas = db.relationship('Sistema', secondary=funcionario_sistemas, lazy='subquery',
                               backref=db.backref('funcionarios', lazy=True))

class Sistema(db.Model):
    """
    Catálogo de todos os sistemas, benefícios ou acessos que podem ser concedidos.
    Ex: 'Email Corporativo', 'Gympass', 'Plano de Saúde', 'Active Directory'
    """
    __tablename__ = 'sistema'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    categoria = db.Column(db.String(50)) # Ex: 'Benefício', 'Acesso TI', 'Software'

class Aviso(db.Model):
    """
    Mural de avisos para comunicados da empresa.
    """
    __tablename__ = 'aviso'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    # Relações
    autor = db.relationship('Usuario')
    logs_ciencia = db.relationship('LogCienciaAviso', backref='aviso', lazy='dynamic')

class LogCienciaAviso(db.Model):
    """
    Registra quando um usuário deu ciência em um aviso.
    """
    __tablename__ = 'log_ciencia_aviso'
    id = db.Column(db.Integer, primary_key=True)
    aviso_id = db.Column(db.Integer, db.ForeignKey('aviso.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_ciencia = db.Column(db.DateTime, default=datetime.utcnow)

    # Relações
    usuario = db.relationship('Usuario', backref=db.backref('logs_ciencia', lazy='dynamic'))

class Documento(db.Model):
    """
    Armazena metadados de documentos dos funcionários.
    O arquivo em si ficará na nuvem (ex: S3) ou servidor local.
    """
    __tablename__ = 'documento'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    tipo_documento = db.Column(db.String(100), nullable=False) # 'Contrato', 'RG', 'Contracheque'
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True) # URL do S3 ou caminho do arquivo
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)

    # Relações
    funcionario = db.relationship('Funcionario', backref='documentos')

class Feedback(db.Model):
    """
    Registra os feedbacks dados aos colaboradores.
    """
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    feedback = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    # IDs de quem deu e quem recebeu o feedback
    avaliador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    avaliado_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)

    # Relações
    avaliador = db.relationship('Usuario', foreign_keys=[avaliador_id])
    avaliado = db.relationship('Funcionario', foreign_keys=[avaliado_id])