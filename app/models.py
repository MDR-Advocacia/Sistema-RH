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

# --- Modelos Principais ---

class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer, primary_key=True)

    # CAMPO ADICIONADO: Essencial para o login e vínculo com o AD
    username = db.Column(db.String(120), unique=True, nullable=True, index=True)

    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), unique=True)
    senha_provisoria = db.Column(db.Boolean, default=True, nullable=False)
    data_consentimento = db.Column(db.DateTime, nullable=True)
    theme = db.Column(db.String(50), default='light', nullable=False)

    # --- CAMPOS ADICIONADOS PARA O PIPELINE DE DOCUMENTOS E SYNC AD ---
    ultimo_login_em = db.Column(db.DateTime, nullable=True)
    ultimo_logon_ad = db.Column(db.DateTime, nullable=True) # NOVO CAMPO PARA LAST LOGON
    primeiro_login_completo = db.Column(db.Boolean, default=False, nullable=False)
    # --- FIM DOS CAMPOS ADICIONADOS ---


    funcionario = db.relationship('Funcionario', backref=db.backref('usuario', uselist=False))
    permissoes = db.relationship('Permissao', secondary=permissoes_usuarios, lazy='subquery',
                                 backref=db.backref('usuarios', lazy=True))

    def set_password(self, password):
        # CORREÇÃO DE COMPATIBILIDADE (Erro do 'scrypt' no macOS)
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
    
    status = db.Column(db.String(50), default='Pendente', nullable=False, index=True)
    data_requisicao = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    data_conclusao = db.Column(db.DateTime, nullable=True)
    data_ultima_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    observacoes_rh = db.Column(db.Text, nullable=True) 

    tipo_documento_id = db.Column(db.Integer, db.ForeignKey('tipo_documento.id'), nullable=False)
    destinatario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False, index=True)
    documento_enviado_id = db.Column(db.Integer, db.ForeignKey('documento.id'), nullable=True)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)

    tipo = db.relationship('TipoDocumento', backref='requisicoes')
    destinatario = db.relationship('Funcionario', backref=db.backref('requisicoes_documentos', lazy='dynamic'))
    documento = db.relationship('Documento', backref='requisicao', uselist=False, foreign_keys=[documento_enviado_id])
    solicitante = db.relationship('Usuario')


class TipoDocumento(db.Model):
    __tablename__ = 'tipo_documento'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.String(255), nullable=True)
    obrigatorio_na_admissao = db.Column(db.Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<TipoDocumento {self.nome}>'


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

    def __repr__(self):
        return f'<Denuncia "{self.titulo}">'

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

    def __repr__(self):
        return f'<Log {self.timestamp}: {self.acao}>'

# --- NOVOS MODELOS ADICIONADOS ---
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

    def __repr__(self):
        return f'<VinculoADSugestao {self.funcionario_nome} -> {self.ad_display_name}>'
    
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

    def __repr__(self):
        return f'<Artigo {self.titulo}>'

# --- FASE 1: MÓDULO HELPDESK E ATIVOS ---

class Localizacao(db.Model):
    """ Modelo para Localizações Físicas (Salas, Mesas) """
    __tablename__ = 'localizacao'
    id = db.Column(db.Integer, primary_key=True)
    nome_sala = db.Column(db.String(100), nullable=False, unique=True)
    andar = db.Column(db.String(50), nullable=True)
    planta_path = db.Column(db.String(255), nullable=True) # Caminho para imagem da planta/mapa

    def __repr__(self):
        return f'<Localizacao {self.nome_sala}>'

class Ativo(db.Model):
    """ Modelo para o Inventário Central (CMDB) """
    __tablename__ = 'ativo'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    hostname = db.Column(db.String(100), unique=True, nullable=True, index=True)
    tag_patrimonio = db.Column(db.String(100), unique=True, nullable=True, index=True)
    numero_serie = db.Column(db.String(100), unique=True, nullable=True, index=True)
    
    tipo = db.Column(db.String(50), default='Desktop', nullable=False)
    status = db.Column(db.String(50), default='Em Uso', nullable=False)
    
    localizacao_id = db.Column(db.Integer, db.ForeignKey('localizacao.id'), nullable=True)
    
    # --- NOVO CAMPO: SETOR DO ATIVO ---
    setor_id = db.Column(db.Integer, db.ForeignKey('setor.id'), nullable=True)
    # ----------------------------------

    localizacao = db.relationship('Localizacao', backref='ativos')
    setor = db.relationship('Setor', backref='ativos') # Relacionamento
    
    descricao_ad = db.Column(db.String(255), nullable=True)
    sistema_operacional = db.Column(db.String(100), nullable=True)
    ultimo_logon_ad = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Ativo {self.nome} ({self.hostname})>'

class Emprestimo(db.Model):
    """ Modelo para Cautela (Check-out/Check-in de Notebooks) """
    __tablename__ = 'emprestimo'
    id = db.Column(db.Integer, primary_key=True)
    
    ativo_id = db.Column(db.Integer, db.ForeignKey('ativo.id'), nullable=False)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
    tecnico_responsavel_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # Quem entregou
    
    data_emprestimo = db.Column(db.DateTime, default=datetime.utcnow)
    data_prevista_devolucao = db.Column(db.Date, nullable=True)
    data_devolucao_real = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(50), default='Ativo', nullable=False) # "Ativo", "Devolvido"

    ativo = db.relationship('Ativo', backref='emprestimos')
    funcionario = db.relationship('Funcionario', backref='emprestimos')
    tecnico_responsavel = db.relationship('Usuario')

    def __repr__(self):
        return f'<Emprestimo Ativo {self.ativo_id} para Func {self.funcionario_id}>'

class CategoriaTI(db.Model):
    """ Categorias para os chamados de Helpdesk (Ex: Hardware, Rede, Sistema) """
    __tablename__ = 'categoria_ti'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False)
    
    def __repr__(self):
        return f'<CategoriaTI {self.nome}>'

class ChamadoTI(db.Model):
    """ Modelo para os Chamados de Helpdesk (Baseado em Denuncia) """
    __tablename__ = 'chamado_ti'
    id = db.Column(db.Integer, primary_key=True)
    
    # --- NOVO CAMPO: PROTOCOLO ---
    protocolo = db.Column(db.String(20), unique=True, nullable=True, index=True)
    
    # --- NOVO CAMPO: ARQUIVADO (Fase 1.6) ---
    arquivado = db.Column(db.Boolean, default=False, nullable=False)
    # ----------------------------------------

    titulo = db.Column(db.String(200), nullable=False)
    conteudo = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='Aberto', nullable=False) # Aberto, Em Andamento, Pendente, Fechado
    prioridade = db.Column(db.String(50), default='Media', nullable=False) # Baixa, Media, Alta, Urgente
    data_abertura = db.Column(db.DateTime, default=datetime.utcnow)
    data_fechamento = db.Column(db.DateTime, nullable=True)
    data_limite_sla = db.Column(db.DateTime, nullable=True)
    
    # Relacionamentos
    categoria_ti_id = db.Column(db.Integer, db.ForeignKey('categoria_ti.id'), nullable=False)
    solicitante_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    tecnico_atribuido_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=True)
    ativo_associado_id = db.Column(db.Integer, db.ForeignKey('ativo.id'), nullable=True) # Link com QR Code

    categoria = db.relationship('CategoriaTI', backref='chamados')
    solicitante = db.relationship('Usuario', foreign_keys=[solicitante_id], backref='chamados_abertos')
    tecnico_atribuido = db.relationship('Usuario', foreign_keys=[tecnico_atribuido_id], backref='chamados_atribuidos')
    ativo_associado = db.relationship('Ativo', backref='chamados')
    
    anexos = db.relationship('ChamadoAnexo', backref='chamado', lazy='dynamic', cascade="all, delete-orphan")
    comentarios = db.relationship('ChamadoComentario', backref='chamado', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<ChamadoTI {self.id}: {self.titulo}>'

class ChamadoAnexo(db.Model):
    """ Anexos para os Chamados (Baseado em DenunciaAnexo) """
    __tablename__ = 'chamado_anexo'
    id = db.Column(db.Integer, primary_key=True)
    nome_arquivo_original = db.Column(db.String(255), nullable=False)
    path_armazenamento = db.Column(db.String(512), nullable=False, unique=True)
    chamado_id = db.Column(db.Integer, db.ForeignKey('chamado_ti.id'), nullable=False)

class ChamadoComentario(db.Model):
    """ Histórico de comentários (idas e vindas) dos chamados """
    __tablename__ = 'chamado_comentario'
    id = db.Column(db.Integer, primary_key=True)
    comentario = db.Column(db.Text, nullable=False)
    data_comentario = db.Column(db.DateTime, default=datetime.utcnow)
    
    chamado_id = db.Column(db.Integer, db.ForeignKey('chamado_ti.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False) # Quem comentou (solicitante ou técnico)

    usuario = db.relationship('Usuario')