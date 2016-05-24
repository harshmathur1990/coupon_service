"""removed expired_at and added index on all_vouchers.code

Revision ID: 4cc3ff5d232a
Revises: 31ebbe231b76
Create Date: 2016-04-06 18:29:09.010665

"""

# revision identifiers, used by Alembic.
revision = '4cc3ff5d232a'
down_revision = '31ebbe231b76'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_all_vouchers_code'), 'all_vouchers', ['code'], unique=False)
    op.drop_column('all_vouchers', 'expired_at')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('all_vouchers', sa.Column('expired_at', mysql.DATETIME(), nullable=True))
    op.drop_index(op.f('ix_all_vouchers_code'), table_name='all_vouchers')
    ### end Alembic commands ###
