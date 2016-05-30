"""indexes on use tracker and log

Revision ID: 523481691123
Revises: 68e7e1dd739d
Create Date: 2016-04-11 19:04:30.100537

"""

# revision identifiers, used by Alembic.
revision = '523481691123'
down_revision = '68e7e1dd739d'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_index('user_voucher_transaction_log_user_id', 'user_voucher_transaction_log', ['user_id'], unique=False)
    op.create_index('user_voucher_transaction_log_user_id_voucher_id', 'user_voucher_transaction_log', ['user_id', 'voucher_id'], unique=False)
    op.create_index('user_voucher_transaction_log_voucher_id', 'user_voucher_transaction_log', ['voucher_id'], unique=False)
    op.create_index('voucher_use_tracker_user_id', 'voucher_use_tracker', ['user_id'], unique=False)
    op.create_index('voucher_use_tracker_user_id_voucher_id', 'voucher_use_tracker', ['user_id', 'voucher_id'], unique=False)
    op.create_index('voucher_use_tracker_voucher_id', 'voucher_use_tracker', ['voucher_id'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('voucher_use_tracker_voucher_id', table_name='voucher_use_tracker')
    op.drop_index('voucher_use_tracker_user_id_voucher_id', table_name='voucher_use_tracker')
    op.drop_index('voucher_use_tracker_user_id', table_name='voucher_use_tracker')
    op.drop_index('user_voucher_transaction_log_voucher_id', table_name='user_voucher_transaction_log')
    op.drop_index('user_voucher_transaction_log_user_id_voucher_id', table_name='user_voucher_transaction_log')
    op.drop_index('user_voucher_transaction_log_user_id', table_name='user_voucher_transaction_log')
    ### end Alembic commands ###