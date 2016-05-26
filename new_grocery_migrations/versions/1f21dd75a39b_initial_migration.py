"""initial migration

Revision ID: 1f21dd75a39b
Revises: None
Create Date: 2016-05-24 15:17:59.442780

"""

# revision identifiers, used by Alembic.
revision = '1f21dd75a39b'
down_revision = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tokens',
    sa.Column('token', sa.VARCHAR(length=250), nullable=False),
    sa.Column('agent_id', mysql.INTEGER(), nullable=False),
    sa.Column('agent_name', sa.VARCHAR(length=250), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('last_accessed_at', mysql.DATETIME(fsp=6), nullable=True),
    sa.PrimaryKeyConstraint('token')
    )
    op.create_index(op.f('ix_tokens_agent_id'), 'tokens', ['agent_id'], unique=True)
    op.create_index(op.f('ix_tokens_agent_name'), 'tokens', ['agent_name'], unique=True)
    op.create_table('all_vouchers',
    sa.Column('id', sa.BINARY(length=16), nullable=False),
    sa.Column('code', sa.VARCHAR(length=200), nullable=False),
    sa.Column('rules', sa.VARCHAR(length=150), nullable=False),
    sa.Column('custom', sa.VARCHAR(length=1000), nullable=True),
    sa.Column('description', sa.VARCHAR(length=255), nullable=True),
    sa.Column('from', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('to', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('schedule', sa.VARCHAR(length=250), nullable=True),
    sa.Column('mutable', mysql.TINYINT(unsigned=True), nullable=True),
    sa.Column('type', mysql.TINYINT(unsigned=True), nullable=False),
    sa.Column('created_by', sa.VARCHAR(length=32), nullable=False),
    sa.Column('updated_by', sa.VARCHAR(length=32), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('agent_id', mysql.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['tokens.agent_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_all_vouchers_code'), 'all_vouchers', ['code'], unique=False)
    op.create_table('rule',
    sa.Column('id', sa.BINARY(length=16), nullable=False),
    sa.Column('name', sa.VARCHAR(length=255), nullable=True),
    sa.Column('description', sa.VARCHAR(length=255), nullable=True),
    sa.Column('criteria_json', sa.VARCHAR(length=2000), nullable=False),
    sa.Column('blacklist_criteria_json', sa.VARCHAR(length=2000), nullable=True),
    sa.Column('benefits_json', sa.VARCHAR(length=1000), nullable=False),
    sa.Column('sha2hash', sa.VARCHAR(length=64), nullable=True),
    sa.Column('active', mysql.TINYINT(unsigned=True), nullable=True),
    sa.Column('created_by', sa.VARCHAR(length=32), nullable=False),
    sa.Column('updated_by', sa.VARCHAR(length=32), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('agent_id', mysql.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['tokens.agent_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rule_sha2hash'), 'rule', ['sha2hash'], unique=False)
    op.create_table('vouchers',
    sa.Column('id', sa.BINARY(length=16), nullable=False),
    sa.Column('code', sa.VARCHAR(length=200), nullable=False),
    sa.Column('rules', sa.VARCHAR(length=150), nullable=False),
    sa.Column('custom', sa.VARCHAR(length=1000), nullable=True),
    sa.Column('description', sa.VARCHAR(length=255), nullable=True),
    sa.Column('from', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('to', mysql.DATETIME(fsp=6), nullable=True),
    sa.Column('schedule', sa.VARCHAR(length=250), nullable=True),
    sa.Column('mutable', mysql.TINYINT(unsigned=True), nullable=True),
    sa.Column('type', mysql.TINYINT(unsigned=True), nullable=False),
    sa.Column('created_by', sa.VARCHAR(length=32), nullable=False),
    sa.Column('updated_by', sa.VARCHAR(length=32), nullable=False),
    sa.Column('created_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('updated_at', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('agent_id', mysql.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['tokens.agent_id'], ),
    sa.PrimaryKeyConstraint('code'),
    sa.UniqueConstraint('id')
    )
    op.create_table('auto_benefits',
    sa.Column('id', mysql.BIGINT(), nullable=False),
    sa.Column('type', mysql.INTEGER(), nullable=False),
    sa.Column('variants', mysql.INTEGER(), nullable=True),
    sa.Column('zone', mysql.INTEGER(), nullable=False),
    sa.Column('range_min', mysql.INTEGER(), nullable=True),
    sa.Column('range_max', mysql.INTEGER(), nullable=True),
    sa.Column('cart_range_min', mysql.INTEGER(), nullable=True),
    sa.Column('cart_range_max', mysql.INTEGER(), nullable=True),
    sa.Column('voucher_id', sa.BINARY(length=16), nullable=False),
    sa.Column('from', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('to', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('agent_id', mysql.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['tokens.agent_id'], ),
    sa.ForeignKeyConstraint(['voucher_id'], ['all_vouchers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_auto_benefits_cart_range_max'), 'auto_benefits', ['cart_range_max'], unique=False)
    op.create_index(op.f('ix_auto_benefits_cart_range_min'), 'auto_benefits', ['cart_range_min'], unique=False)
    op.create_index(op.f('ix_auto_benefits_from'), 'auto_benefits', ['from'], unique=False)
    op.create_index(op.f('ix_auto_benefits_range_max'), 'auto_benefits', ['range_max'], unique=False)
    op.create_index(op.f('ix_auto_benefits_range_min'), 'auto_benefits', ['range_min'], unique=False)
    op.create_index(op.f('ix_auto_benefits_to'), 'auto_benefits', ['to'], unique=False)
    op.create_index(op.f('ix_auto_benefits_type'), 'auto_benefits', ['type'], unique=False)
    op.create_index(op.f('ix_auto_benefits_variants'), 'auto_benefits', ['variants'], unique=False)
    op.create_index(op.f('ix_auto_benefits_voucher_id'), 'auto_benefits', ['voucher_id'], unique=False)
    op.create_index(op.f('ix_auto_benefits_zone'), 'auto_benefits', ['zone'], unique=False)
    op.create_table('user_voucher_transaction_log',
    sa.Column('id', sa.BINARY(length=16), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=32), nullable=False),
    sa.Column('updated_on', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('voucher_id', sa.BINARY(length=16), nullable=False),
    sa.Column('order_id', sa.VARCHAR(length=32), nullable=False),
    sa.Column('status', mysql.TINYINT(unsigned=True), nullable=False),
    sa.Column('response', sa.VARCHAR(length=8000), nullable=True),
    sa.Column('agent_id', mysql.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['tokens.agent_id'], ),
    sa.ForeignKeyConstraint(['voucher_id'], ['all_vouchers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('user_voucher_transaction_log_user_id', 'user_voucher_transaction_log', ['user_id'], unique=False)
    op.create_index('user_voucher_transaction_log_user_id_voucher_id', 'user_voucher_transaction_log', ['user_id', 'voucher_id'], unique=False)
    op.create_index('user_voucher_transaction_log_voucher_id', 'user_voucher_transaction_log', ['voucher_id'], unique=False)
    op.create_table('voucher_use_tracker',
    sa.Column('id', sa.BINARY(length=16), nullable=False),
    sa.Column('user_id', sa.VARCHAR(length=32), nullable=False),
    sa.Column('applied_on', mysql.DATETIME(fsp=6), nullable=False),
    sa.Column('voucher_id', sa.BINARY(length=16), nullable=False),
    sa.Column('order_id', sa.VARCHAR(length=32), nullable=False),
    sa.Column('response', sa.VARCHAR(length=8000), nullable=True),
    sa.Column('agent_id', mysql.INTEGER(), nullable=True),
    sa.ForeignKeyConstraint(['agent_id'], ['tokens.agent_id'], ),
    sa.ForeignKeyConstraint(['voucher_id'], ['all_vouchers.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('voucher_use_tracker_user_id', 'voucher_use_tracker', ['user_id'], unique=False)
    op.create_index('voucher_use_tracker_user_id_voucher_id', 'voucher_use_tracker', ['user_id', 'voucher_id'], unique=False)
    op.create_index('voucher_use_tracker_voucher_id', 'voucher_use_tracker', ['voucher_id'], unique=False)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('voucher_use_tracker_voucher_id', table_name='voucher_use_tracker')
    op.drop_index('voucher_use_tracker_user_id_voucher_id', table_name='voucher_use_tracker')
    op.drop_index('voucher_use_tracker_user_id', table_name='voucher_use_tracker')
    op.drop_table('voucher_use_tracker')
    op.drop_index('user_voucher_transaction_log_voucher_id', table_name='user_voucher_transaction_log')
    op.drop_index('user_voucher_transaction_log_user_id_voucher_id', table_name='user_voucher_transaction_log')
    op.drop_index('user_voucher_transaction_log_user_id', table_name='user_voucher_transaction_log')
    op.drop_table('user_voucher_transaction_log')
    op.drop_index(op.f('ix_auto_benefits_zone'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_voucher_id'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_variants'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_type'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_to'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_range_min'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_range_max'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_from'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_cart_range_min'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_cart_range_max'), table_name='auto_benefits')
    op.drop_table('auto_benefits')
    op.drop_table('vouchers')
    op.drop_index(op.f('ix_rule_sha2hash'), table_name='rule')
    op.drop_table('rule')
    op.drop_index(op.f('ix_all_vouchers_code'), table_name='all_vouchers')
    op.drop_table('all_vouchers')
    op.drop_index(op.f('ix_tokens_agent_name'), table_name='tokens')
    op.drop_index(op.f('ix_tokens_agent_id'), table_name='tokens')
    op.drop_table('tokens')
    ### end Alembic commands ###
