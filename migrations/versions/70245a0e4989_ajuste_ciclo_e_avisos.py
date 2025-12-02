"""ajuste_ciclo_e_avisos

Revision ID: 70245a0e4989
Revises: fb3149e32bbb
Create Date: 2024-11-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = '70245a0e4989'
down_revision = 'fb3149e32bbb'
branch_labels = None
depends_on = None


def upgrade():
    # Cria um inspetor para verificar o banco
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Obtém colunas existentes na tabela 'aviso'
    existing_columns = [col['name'] for col in inspector.get_columns('aviso')]

    with op.batch_alter_table('aviso', schema=None) as batch_op:
        # Só adiciona se não existir
        if 'target_supervisores' not in existing_columns:
            batch_op.add_column(sa.Column('target_supervisores', sa.Boolean(), nullable=False, server_default='false'))
        
        # Se houver outras colunas nessa migração, faça o mesmo check
        # Exemplo (ajuste conforme o original se tiver mais campos):
        # if 'outro_campo' not in existing_columns:
        #    batch_op.add_column(...)

    # Se essa migração criava tabelas, use o check também:
    # if 'nome_tabela' not in inspector.get_table_names():
    #     op.create_table(...)


def downgrade():
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    existing_columns = [col['name'] for col in inspector.get_columns('aviso')]

    with op.batch_alter_table('aviso', schema=None) as batch_op:
        if 'target_supervisores' in existing_columns:
            batch_op.drop_column('target_supervisores')