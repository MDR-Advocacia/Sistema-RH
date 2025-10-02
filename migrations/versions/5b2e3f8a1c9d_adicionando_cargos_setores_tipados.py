"""Adiciona tabelas Cargo e Setor e atualiza Funcionario

Revision ID: 5b2e3f8a1c9d
Revises: 1ee9d493b860
Create Date: 2025-10-02 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5b2e3f8a1c9d'
down_revision = '1ee9d493b860' # Coloque aqui o ID da última migração
branch_labels = None
depends_on = None

def upgrade():
    # ### Cria as novas tabelas ###
    op.create_table('cargo',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )
    op.create_table('setor',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('nome')
    )

    # ### Altera a tabela funcionario ###
    with op.batch_alter_table('funcionario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cargo_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('setor_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_funcionario_cargo', 'cargo', ['cargo_id'], ['id'])
        batch_op.create_foreign_key('fk_funcionario_setor', 'setor', ['setor_id'], ['id'])
        batch_op.drop_column('cargo')
        batch_op.drop_column('setor')

def downgrade():
    # ### Reverte as alterações na tabela funcionario ###
    with op.batch_alter_table('funcionario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('setor', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
        batch_op.add_column(sa.Column('cargo', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
        batch_op.drop_constraint('fk_funcionario_setor', type_='foreignkey')
        batch_op.drop_constraint('fk_funcionario_cargo', type_='foreignkey')
        batch_op.drop_column('setor_id')
        batch_op.drop_column('cargo_id')

    # ### Remove as novas tabelas ###
    op.drop_table('setor')
    op.drop_table('cargo')