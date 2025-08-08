"""Adiciona tipo de ajuste na tabela ponto

Revision ID: e371d2b26df8
Revises: eba38c024b66
Create Date: 2025-08-08 13:25:21.499428

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e371d2b26df8'
down_revision = 'eba38c024b66' # ID da migração anterior
branch_labels = None
depends_on = None


def upgrade():
    # Passo 1: Adiciona a coluna, mas permite que ela seja nula temporariamente.
    with op.batch_alter_table('ponto', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tipo_ajuste', sa.String(length=50), nullable=True))

    # Passo 2: Preenche todas as linhas existentes com um valor padrão.
    # Isso garante que nenhuma linha terá um valor nulo.
    op.execute("UPDATE ponto SET tipo_ajuste = 'Ajuste Geral' WHERE tipo_ajuste IS NULL")

    # Passo 3: Agora que não há mais nulos, altera a coluna para ser NOT NULL.
    with op.batch_alter_table('ponto', schema=None) as batch_op:
        batch_op.alter_column('tipo_ajuste',
               existing_type=sa.String(length=50),
               nullable=False)


def downgrade():
    # Para reverter, simplesmente removemos a coluna.
    with op.batch_alter_table('ponto', schema=None) as batch_op:
        batch_op.drop_column('tipo_ajuste')