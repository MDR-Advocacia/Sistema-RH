from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class TipoDocumentoForm(FlaskForm):
    """Formulário para criar e editar Tipos de Documento."""
    nome = StringField(
        'Nome do Documento', 
        validators=[DataRequired(message="O nome é obrigatório."), Length(min=3, max=100)]
    )
    descricao = TextAreaField(
        'Descrição (Opcional)', 
        validators=[Length(max=255)]
    )
    obrigatorio_na_admissao = BooleanField(
        'Obrigatório na Admissão?'
    )
    submit = SubmitField('Salvar')