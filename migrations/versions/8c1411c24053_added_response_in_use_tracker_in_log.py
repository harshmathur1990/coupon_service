"""added response in use tracker in log

Revision ID: 8c1411c24053
Revises: bbd11511743f
Create Date: 2016-04-04 20:16:47.369184

"""

# revision identifiers, used by Alembic.
revision = '8c1411c24053'
down_revision = 'bbd11511743f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_voucher_transaction_log', sa.Column('response', sa.VARCHAR(length=8000), nullable=True))
    op.add_column('voucher_use_tracker', sa.Column('response', sa.VARCHAR(length=8000), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('voucher_use_tracker', 'response')
    op.drop_column('user_voucher_transaction_log', 'response')
    ### end Alembic commands ###