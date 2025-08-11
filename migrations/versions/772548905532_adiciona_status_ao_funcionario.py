"""Adiciona status ao funcionario

Revision ID: 772548905532
Revises: e371d2b26df8
Create Date: 2025-08-11 12:39:20.983682

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '772548905532'
down_revision = 'e371d2b26df8'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona a coluna permitindo nulos temporariamente
    with op.batch_alter_table('funcionario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=50), nullable=True))

    # Define 'Ativo' para todos os funcionários existentes
    op.execute("UPDATE funcionario SET status = 'Ativo' WHERE status IS NULL")

    # Altera a coluna para não permitir nulos
    with op.batch_alter_table('funcionario', schema=None) as batch_op:
        batch_op.alter_column('status', existing_type=sa.String(length=50), nullable=False)

def downgrade():
    with op.batch_alter_table('funcionario', schema=None) as batch_op:
        batch_op.drop_column('status')