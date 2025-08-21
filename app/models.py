# app/mos.py
import jwt

from flask import current_app
from datetime import datetime, timedelta, timezone
from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash # type: ignore
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Text, DateTime, Boolean # type: ignore # Adicione Boolean
from flask_login import UserMixin # type: ignore

# --- Tabelas de Associação ---

permissoes_usuarios = db.Table('permissoes_usuarios',
    db.Column('usuario_id', db.Integer, db.ForeignKey('usuario.id'), primary_key=True),
    db.Column('permissao_id', db.Integer, db.ForeignKey('permissao.id'), primary_key=True)
)

funcionario_sistemas = db.Table('funcionario_sistemas',
    db.Column('funcionario_id', db.Integer, db.ForeignKey('funcionario.id'), primary_key=True),
    db.Column('sistema_id', db.Integer, db.ForeignKey('sistema.id'), primary_key=True),
    db.Column('status', db.String(50), default='Ativo'),
    db.Column('observacao', db.String(255))
)

# --- Modelos Principais ---

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), unique=True)
    senha_provisoria = db.Column(db.Boolean, default=True, nullable=False)
    data_consentimento = db.Column(db.DateTime, nullable=True)

    funcionario = db.relationship('Funcionario', backref=db.backref('usuario', uselist=False))
    permissoes = db.relationship('Permissao', secondary=permissoes_usuarios, lazy='subquery',
                                 backref=db.backref('usuarios', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def tem_permissao(self, nome_permissao):
        if isinstance(nome_permissao, list):
            return any(p.nome in nome_permissao for p in self.permissoes)
        return any(p.nome == nome_permissao for p in self.permissoes)
    
    def get_reset_password_token(self, expires_in=600):
        """Gera um token seguro para redefinição de senha."""
        return jwt.encode(
            {
                "reset_password": self.id,
                "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            },
            current_app.config['SECRET_KEY'],
            algorithm="HS256"
        )

    @staticmethod
    def verify_reset_password_token(token):
        """Verifica o token de redefinição e retorna o usuário se for válido."""
        try:
            id = jwt.decode(
                token,
                current_app.config['SECRET_KEY'],
                algorithms=["HS256"]
            )['reset_password']
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None
        return db.session.get(Usuario, id)

class Permissao(db.Model):
    __tablename__ = 'permissao'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(255))

class Funcionario(db.Model):
    __tablename__ = 'funcionario'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(50), default='Ativo', nullable=False)
    cpf = db.Column(db.String(25), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(50))
    cargo = db.Column(db.String(100))
    setor = db.Column(db.String(100))
    data_nascimento = db.Column(db.Date)
    contato_emergencia_nome = db.Column(db.String(120))
    contato_emergencia_telefone = db.Column(db.String(50))
    foto_perfil = db.Column(db.String(255), nullable=True)
    apelido = db.Column(db.String(50), nullable=True)
    data_desligamento = db.Column(db.Date, nullable=True)

    sistemas = db.relationship('Sistema', secondary=funcionario_sistemas, lazy='subquery',
                               backref=db.backref('funcionarios', lazy=True))

class Sistema(db.Model):
    __tablename__ = 'sistema'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    categoria = db.Column(db.String(50))

class Aviso(db.Model):
    __tablename__ = 'aviso'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, default=datetime.utcnow)
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    autor = db.relationship('Usuario')
    logs_ciencia = db.relationship('LogCienciaAviso', backref='aviso', lazy='dynamic', cascade="all, delete-orphan")
    anexos = db.relationship('AvisoAnexo', backref='aviso', lazy='dynamic', cascade="all, delete-orphan")
    arquivado = db.Column(db.Boolean, default=False, nullable=False)

class LogCienciaAviso(db.Model):
    __tablename__ = 'log_ciencia_aviso'
    id = db.Column(db.Integer, primary_key=True)
    aviso_id = db.Column(db.Integer, db.ForeignKey('aviso.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_ciencia = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship('Usuario', backref=db.backref('logs_ciencia', lazy='dynamic'))

class AvisoAnexo(db.Model):
    __tablename__ = 'aviso_anexo'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo_original = db.Column(db.String(255), nullable=False)
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True)
    aviso_id = db.Column(db.Integer, db.ForeignKey('aviso.id'), nullable=False)    

class Documento(db.Model):
    __tablename__ = 'documento'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    tipo_documento = db.Column(db.String(100), nullable=False)
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao_documento.id'), nullable=True)

    # --- CAMPOS ADICIONADOS PARA O FLUXO DE REVISÃO ---
    status = db.Column(db.String(50), default='Pendente de Revisão', nullable=False)
    revisor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    data_revisao = db.Column(db.DateTime, nullable=True)
    observacao_revisao = db.Column(db.Text, nullable=True)

    funcionario = db.relationship('Funcionario', backref='documentos')
    revisor = db.relationship('Usuario', foreign_keys=[revisor_id])
    # ----------------------------------------------------

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    feedback = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    avaliador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    avaliado_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)

    avaliador = db.relationship('Usuario', foreign_keys=[avaliador_id])
    avaliado = db.relationship('Funcionario', foreign_keys=[avaliado_id])

class RequisicaoDocumento(db.Model):
    __tablename__ = 'requisicao_documento'
    id = db.Column(db.Integer, primary_key=True)
    tipo_documento = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='Pendente', nullable=False)
    data_requisicao = db.Column(db.DateTime, default=datetime.utcnow)
    data_conclusao = db.Column(db.DateTime, nullable=True)
    observacao = db.Column(db.Text, nullable=True) 
    
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)

    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id])
    destinatario = db.relationship('Funcionario', backref='requisicoes')


## Modelo de pontos
class Ponto(db.Model):
    __tablename__ = 'ponto'
    id = db.Column(db.Integer, primary_key=True)
    data_ajuste = db.Column(db.Date, nullable=False)
    tipo_ajuste = db.Column(db.String(50), nullable=False) # Ex: 'Entrada', 'Saída Almoço', etc.
    justificativa = db.Column(db.Text, nullable=True) # Justificativa do colaborador
    path_assinado = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(50), default='Pendente', nullable=False)
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_upload = db.Column(db.DateTime, nullable=True)
    observacao_rh = db.Column(db.Text, nullable=True) # Motivo da reprovação pelo RH

    # Relacionamentos
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    revisor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    
    funcionario = db.relationship('Funcionario', backref='pontos')
    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id])
    revisor = db.relationship('Usuario', foreign_keys=[revisor_id])