"""added columns session_id and user_uuid

Revision ID: ce6cc68645e8
Revises: cd3c8318ffcb
Create Date: 2016-07-26 14:38:32.425292

"""

# revision identifiers, used by Alembic.
revision = 'ce6cc68645e8'
down_revision = 'cd3c8318ffcb'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint(None, 'permissions', ['permission'])
    op.add_column('user_voucher_transaction_log', sa.Column('session_id', sa.VARCHAR(length=32), nullable=True))
    op.add_column('user_voucher_transaction_log', sa.Column('user_uuid', sa.VARCHAR(length=32), nullable=True))
    op.add_column('voucher_use_tracker', sa.Column('session_id', sa.VARCHAR(length=32), nullable=True))
    op.add_column('voucher_use_tracker', sa.Column('user_uuid', sa.VARCHAR(length=32), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('voucher_use_tracker', 'user_uuid')
    op.drop_column('voucher_use_tracker', 'session_id')
    op.drop_column('user_voucher_transaction_log', 'user_uuid')
    op.drop_column('user_voucher_transaction_log', 'session_id')
    op.drop_constraint(None, 'permissions', type_='unique')
    ### end Alembic commands ###
