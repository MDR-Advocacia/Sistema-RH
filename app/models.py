from . import db

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    cargo = db.Column(db.String(100), nullable=False)
    setor = db.Column(db.String(100), nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    contato_emergencia_nome = db.Column(db.String(120), nullable=False)
    contato_emergencia_telefone = db.Column(db.String(20), nullable=False)
    beneficios_ativos = db.Column(db.Boolean, default=True, nullable=False)

    sistemas = db.relationship('Sistema', backref='funcionario', lazy=True)



class Sistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(10), nullable=False)  # ativo/inativo
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False)
