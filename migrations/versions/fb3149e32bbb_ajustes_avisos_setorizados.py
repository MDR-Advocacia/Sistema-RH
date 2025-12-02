"""ajustes_avisos_setorizados

Revision ID: fb3149e32bbb
Revises: 4bd3a4cd983e
Create Date: 2024-11-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'fb3149e32bbb'
down_revision = '4bd3a4cd983e'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Cria um "Inspetor" para olhar dentro do banco antes de agir
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # 2. Pega a lista de colunas que JÁ existem na tabela 'aviso'
    existing_columns = [col['name'] for col in inspector.get_columns('aviso')]

    with op.batch_alter_table('aviso', schema=None) as batch_op:
        # 3. Só cria a coluna se ela NÃO estiver na lista
        if 'publico_geral' not in existing_columns:
            batch_op.add_column(sa.Column('publico_geral', sa.Boolean(), nullable=False, server_default='true'))
        
        if 'target_supervisores' not in existing_columns:
            batch_op.add_column(sa.Column('target_supervisores', sa.Boolean(), nullable=False, server_default='false'))
        
        if 'target_diretoria' not in existing_columns:
            batch_op.add_column(sa.Column('target_diretoria', sa.Boolean(), nullable=False, server_default='false'))
        
        if 'arquivado' not in existing_columns:
            batch_op.add_column(sa.Column('arquivado', sa.Boolean(), nullable=False, server_default='false'))

    # 4. Verifica se a tabela auxiliar 'aviso_setores' já existe
    if 'aviso_setores' not in inspector.get_table_names():
        op.create_table('aviso_setores',
            sa.Column('aviso_id', sa.Integer(), nullable=False),
            sa.Column('setor_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['aviso_id'], ['aviso.id'], ),
            sa.ForeignKeyConstraint(['setor_id'], ['setor.id'], ),
            sa.PrimaryKeyConstraint('aviso_id', 'setor_id')
        )


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('aviso')]

    if 'aviso_setores' in inspector.get_table_names():
        op.drop_table('aviso_setores')
        
    with op.batch_alter_table('aviso', schema=None) as batch_op:
        if 'arquivado' in existing_columns:
            batch_op.drop_column('arquivado')
        if 'target_diretoria' in existing_columns:
            batch_op.drop_column('target_diretoria')
        if 'target_supervisores' in existing_columns:
            batch_op.drop_column('target_supervisores')
        if 'publico_geral' in existing_columns:
            batch_op.drop_column('publico_geral')