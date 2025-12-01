# app/models.py
import jwt
from flask import current_app
from datetime import datetime, timedelta, timezone
from . import db
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, Text, DateTime, Boolean
from flask_login import UserMixin

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

# Tabela para vincular avisos a múltiplos setores
aviso_setores = db.Table('aviso_setores',
    db.Column('aviso_id', db.Integer, db.ForeignKey('aviso.id'), primary_key=True),
    db.Column('setor_id', db.Integer, db.ForeignKey('setor.id'), primary_key=True)
)

# --- Modelos Principais ---

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(120), unique=True, nullable=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), unique=True)
    senha_provisoria = db.Column(db.Boolean, default=True, nullable=False)
    data_consentimento = db.Column(db.DateTime, nullable=True)
    theme = db.Column(db.String(50), default='light', nullable=False)

    ultimo_login_em = db.Column(db.DateTime, nullable=True)
    ultimo_logon_ad = db.Column(db.DateTime, nullable=True)
    primeiro_login_completo = db.Column(db.Boolean, default=False, nullable=False)

    funcionario = db.relationship('Funcionario', backref=db.backref('usuario', uselist=False))
    permissoes = db.relationship('Permissao', secondary=permissoes_usuarios, lazy='subquery',
                                 backref=db.backref('usuarios', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def tem_permissao(self, nome_permissao):
        """Verifica se o usuário tem uma permissão específica."""
        if isinstance(nome_permissao, list):
            return any(p.nome in nome_permissao for p in self.permissoes)
        return any(p.nome == nome_permissao for p in self.permissoes)
    
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

    cargo_id = db.Column(db.Integer, db.ForeignKey('cargo.id'), nullable=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)
    cargo = db.relationship('Cargo', backref='funcionarios')
    setor = db.relationship('Setor', backref='funcionarios')

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
    
    publico_geral = db.Column(db.Boolean, default=True, nullable=False) 
    target_supervisores = db.Column(db.Boolean, default=False, nullable=False)
    target_diretoria = db.Column(db.Boolean, default=False, nullable=False)
    arquivado = db.Column(db.Boolean, default=False, nullable=False)

    autor = db.relationship('Usuario')
    logs_ciencia = db.relationship('LogCienciaAviso', backref='aviso', lazy='dynamic', cascade="all, delete-orphan")
    anexos = db.relationship('AvisoAnexo', backref='aviso', lazy='dynamic', cascade="all, delete-orphan")
    setores_alvo = db.relationship('Setor', secondary=aviso_setores, backref=db.backref('avisos_exclusivos', lazy='dynamic'))

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

# --- NOVO: MODELOS DE SOLICITAÇÃO COMPLEXA DE DOCUMENTOS ---

class Solicitacao(db.Model):
    """
    O 'Pai' do pedido. Agrupa várias requisições individuais.
    Ex: 'Relatório Mensal de Bônus' criado pelo Financeiro.
    """
    __tablename__ = 'solicitacao'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    status_geral = db.Column(db.String(50), default='Aberta') # Aberta, Concluída, Cancelada

    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id])
    # Relacionamento com as requisições filhas
    requisicoes = db.relationship('RequisicaoDocumento', backref='solicitacao_pai', lazy='dynamic')
    # Lista de quem deve aprovar (workflow definido na criação)
    aprovadores_previstos = db.relationship('SolicitacaoAprovador', backref='solicitacao', lazy='dynamic', cascade="all, delete-orphan")

class SolicitacaoAprovador(db.Model):
    """
    Define QUEM deve aprovar os documentos dessa solicitação.
    """
    __tablename__ = 'solicitacao_aprovador'
    id = db.Column(db.Integer, primary_key=True)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey('solicitacao.id'), nullable=False)
    aprovador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    aprovador = db.relationship('Usuario')

class DocumentoAprovacao(db.Model):
    """
    Rastreia o 'OK' individual de cada aprovador para um documento específico.
    """
    __tablename__ = 'documento_aprovacao'
    id = db.Column(db.Integer, primary_key=True)
    documento_id = db.Column(db.Integer, db.ForeignKey('documento.id'), nullable=False)
    aprovador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    status = db.Column(db.String(50), default='Pendente') # Pendente, Aprovado, Rejeitado
    data_acao = db.Column(db.DateTime, nullable=True)
    observacao = db.Column(db.Text, nullable=True)

    documento = db.relationship('Documento', back_populates='aprovacoes')
    aprovador = db.relationship('Usuario')

# -----------------------------------------------------------

class Documento(db.Model):
    __tablename__ = 'documento'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    tipo_documento = db.Column(db.String(100), nullable=False)
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    
    requisicao_id = db.Column(db.Integer, db.ForeignKey('requisicao_documento.id', use_alter=True), nullable=True)

    # Status geral do documento (só vira 'Aprovado' se todos os DocumentoAprovacao derem OK)
    status = db.Column(db.String(50), default='Pendente de Revisão', nullable=False)
    
    # Campos Legado (Mantidos para compatibilidade, mas preferir usar a tabela DocumentoAprovacao)
    revisor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    data_revisao = db.Column(db.DateTime, nullable=True)
    observacao_revisao = db.Column(db.Text, nullable=True)

    funcionario = db.relationship('Funcionario', backref='documentos')
    # Relacionamento para as aprovações detalhadas
    aprovacoes = db.relationship('DocumentoAprovacao', back_populates='documento', cascade="all, delete-orphan")


class RequisicaoDocumento(db.Model):
    __tablename__ = 'requisicao_documento'
    id = db.Column(db.Integer, primary_key=True)
    
    # FK Nova para a Solicitacao Pai (opcional para manter compatibilidade com o antigo)
    solicitacao_id = db.Column(db.Integer, db.ForeignKey('solicitacao.id'), nullable=True)

    status = db.Column(db.String(50), default='Pendente', nullable=False, index=True)
    data_requisicao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_conclusao = db.Column(db.DateTime, nullable=True)
    data_ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    observacoes_rh = db.Column(db.Text, nullable=True) 

    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipo_documento.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False, index=True)
    
    documento_enviado_id = db.Column(db.Integer, db.ForeignKey('documento.id', use_alter=True), nullable=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)

    tipo = db.relationship('TipoDocumento', backref='requisicoes')
    destinatario = db.relationship('Funcionario', backref=db.backref('requisicoes_documentos', lazy='dynamic'))
    documento = db.relationship('Documento', backref='requisicao', uselist=False, foreign_keys=[documento_enviado_id])
    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id])

class TipoDocumento(db.Model):
    __tablename__ = 'tipo_documento'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.String(255), nullable=True)
    obrigatorio_na_admissao = db.Column(db.Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<TipoDocumento {self.nome}>'

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    feedback = db.Column(db.Text, nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    
    avaliador_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    avaliado_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)

    avaliador = db.relationship('Usuario', foreign_keys=[avaliador_id])
    avaliado = db.relationship('Funcionario', foreign_keys=[avaliado_id])

## Modelo de pontos
class Ponto(db.Model):
    __tablename__ = 'ponto'
    id = db.Column(db.Integer, primary_key=True)
    data_ajuste = db.Column(db.Date, nullable=False)
    tipo_ajuste = db.Column(db.String(50), nullable=False)
    justificativa = db.Column(db.Text, nullable=True)
    path_assinado = db.Column(db.String(512), nullable=True)
    status = db.Column(db.String(50), default='Pendente', nullable=False)
    data_solicitacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_upload = db.Column(db.DateTime, nullable=True)
    observacao_rh = db.Column(db.Text, nullable=True)

    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    revisor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    
    funcionario = db.relationship('Funcionario', backref='pontos')
    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id])
    revisor = db.relationship('Usuario', foreign_keys=[revisor_id])


## Modelo de Denuncias
class Denuncia(db.Model):
    __tablename__ = 'denuncia'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    data_envio = db.Column(db.DateTime, default=datetime.utcnow)
    categoria = db.Column(db.String(100), nullable=False, default='Outros')
    status = db.Column(db.String(50), default='Nova', nullable=False)
    protocolo = db.Column(db.String(32), unique=True, nullable=True, index=True)
    feedback_rh = db.Column(db.Text, nullable=True) 

    anexos = db.relationship('DenunciaAnexo', backref='denuncia', lazy='dynamic', cascade="all, delete-orphan")

class DenunciaAnexo(db.Model):
    __tablename__ = 'denuncia_anexo'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo_original = db.Column(db.String(255), nullable=False)
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True)
    denuncia_id = db.Column(db.Integer, db.ForeignKey('denuncia.id'), nullable=False)

# Modelo de LOGS
class LogAtividade(db.Model):
    __tablename__ = 'log_atividade'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    acao = db.Column(db.String(512), nullable=False)
    
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    usuario = db.relationship('Usuario', backref='logs_atividade')

class Cargo(db.Model):
    __tablename__ = 'cargo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Cargo {self.nome}>'

class Setor(db.Model):
    __tablename__ = 'setor'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<Setor {self.nome}>'

class VinculoADSugestao(db.Model):
    __tablename__ = 'vinculo_ad_sugestao'
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    funcionario_nome = db.Column(db.String(120), nullable=False)
    ad_username = db.Column(db.String(120), nullable=False)
    ad_display_name = db.Column(db.String(120), nullable=False)
    pontuacao = db.Column(db.Integer, nullable=False)
    
    funcionario = db.relationship('Funcionario')
    
class Artigo(db.Model):
    __tablename__ = 'artigos'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(255), nullable=False)
    resumo = db.Column(db.Text, nullable=True)
    conteudo = db.Column(db.Text, nullable=False)
    data_publicacao = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    
    autor_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    autor = db.relationship('Usuario', backref='artigos_publicados')
    
    link_externo = db.Column(db.String(500), nullable=True)
    path_anexo = db.Column(db.String(500), nullable=True)
    nome_anexo_original = db.Column(db.String(255), nullable=True)

class Localizacao(db.Model):
    __tablename__ = 'localizacao'
    id = db.Column(db.Integer, primary_key=True)
    nome_sala = db.Column(db.String(100), nullable=False, unique=True)
    andar = db.Column(db.String(50), nullable=True)
    planta_path = db.Column(db.String(255), nullable=True)

class Ativo(db.Model):
    __tablename__ = 'ativo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    hostname = db.Column(db.String(100), unique=True, nullable=True, index=True)
    tag_patrimonio = db.Column(db.String(100), unique=True, nullable=True, index=True)
    numero_serie = db.Column(db.String(100), unique=True, nullable=True, index=True)
    
    tipo = db.Column(db.String(50), default='Desktop', nullable=False)
    status = db.Column(db.String(50), default='Em Uso', nullable=False)
    
    localizacao_id = db.Column(db.Integer, db.ForeignKey('localizacao.id'), nullable=True)
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)

    localizacao = db.relationship('Localizacao', backref='ativos')
    setor = db.relationship('Setor', backref='ativos')
    
    descricao_ad = db.Column(db.String(255), nullable=True)
    sistema_operacional = db.Column(db.String(100), nullable=True)
    ultimo_logon_ad = db.Column(db.DateTime, nullable=True)

class Emprestimo(db.Model):
    __tablename__ = 'emprestimo'
    id = db.Column(db.Integer, primary_key=True)
    
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativo.id'), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    tecnico_responsavel_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    
    data_emprestimo = db.Column(db.DateTime, default=datetime.utcnow)
    data_prevista_devolucao = db.Column(db.Date, nullable=True)
    data_devolucao_real = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='Ativo', nullable=False)

    ativo = db.relationship('Ativo', backref='emprestimos')
    funcionario = db.relationship('Funcionario', backref='emprestimos')
    tecnico_responsavel = db.relationship('Usuario')

class CategoriaTI(db.Model):
    __tablename__ = 'categoria_ti'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)

class ChamadoTI(db.Model):
    __tablename__ = 'chamado_ti'
    id = db.Column(db.Integer, primary_key=True)
    protocolo = db.Column(db.String(20), unique=True, nullable=True, index=True)
    arquivado = db.Column(db.Boolean, default=False, nullable=False)

    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Aberto', nullable=False)
    prioridade = db.Column(db.String(50), default='Media', nullable=False)
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    data_fechamento = db.Column(db.DateTime, nullable=True)
    data_limite_sla = db.Column(db.DateTime, nullable=True)
    
    categoria_ti_id = db.Column(db.Integer, db.ForeignKey('categoria_ti.id'), nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tecnico_atribuido_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    ativo_associado_id = db.Column(db.Integer, db.ForeignKey('ativo.id'), nullable=True)

    categoria = db.relationship('CategoriaTI', backref='chamados')
    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id], backref='chamados_abertos')
    tecnico_atribuido = db.relationship('Usuario', foreign_keys=[tecnico_atribuido_id], backref='chamados_atribuidos')
    ativo_associado = db.relationship('Ativo', backref='chamados')
    
    anexos = db.relationship('ChamadoAnexo', backref='chamado', lazy='dynamic', cascade="all, delete-orphan")
    comentarios = db.relationship('ChamadoComentario', backref='chamado', lazy='dynamic', cascade="all, delete-orphan")

class ChamadoAnexo(db.Model):
    __tablename__ = 'chamado_anexo'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo_original = db.Column(db.String(255), nullable=False)
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True)
    chamado_id = db.Column(db.Integer, db.ForeignKey('chamado_ti.id'), nullable=False)

class ChamadoComentario(db.Model):
    __tablename__ = 'chamado_comentario'
    id = db.Column(db.Integer, primary_key=True)
    comentario = db.Column(db.Text, nullable=False)
    data_comentario = db.Column(db.DateTime, default=datetime.utcnow)
    
    chamado_id = db.Column(db.Integer, db.ForeignKey('chamado_ti.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

    usuario = db.relationship('Usuario')