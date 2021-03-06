"""fixed indices

Revision ID: a2b3a2dbb40e
Revises: 24102df3f224
Create Date: 2016-07-26 14:49:23.983106

"""

# revision identifiers, used by Alembic.
revision = 'a2b3a2dbb40e'
down_revision = '24102df3f224'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_auto_freebie_search_cart_range_max', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_cart_range_min', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_from', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_range_max', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_range_min', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_to', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_type', table_name='auto_benefits')
    op.drop_index('ix_auto_freebie_search_variants', table_name='auto_benefits')
    op.drop_constraint(u'auto_benefits_ibfk_1', 'auto_benefits', type_='foreignkey')
    op.drop_index('ix_auto_freebie_search_voucher_id', table_name='auto_benefits')
    op.create_foreign_key(u'auto_benefits_ibfk_1', 'auto_benefits', 'all_vouchers', ['voucher_id'], ['id'])
    op.drop_index('ix_auto_freebie_search_zone', table_name='auto_benefits')
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
    op.create_unique_constraint('uq_permission', 'permissions', ['permission'])
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('uq_permission', 'permissions', type_='unique')
    op.drop_index(op.f('ix_auto_benefits_zone'), table_name='auto_benefits')
    op.drop_constraint(u'auto_benefits_ibfk_1', 'auto_benefits', type_='foreignkey')
    op.drop_index(op.f('ix_auto_benefits_voucher_id'), table_name='auto_benefits')
    op.create_foreign_key(u'auto_benefits_ibfk_1', 'auto_benefits', 'all_vouchers', ['voucher_id'], ['id'])
    op.drop_index(op.f('ix_auto_benefits_variants'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_type'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_to'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_range_min'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_range_max'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_from'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_cart_range_min'), table_name='auto_benefits')
    op.drop_index(op.f('ix_auto_benefits_cart_range_max'), table_name='auto_benefits')
    op.create_index('ix_auto_freebie_search_zone', 'auto_benefits', ['zone'], unique=False)
    op.create_index('ix_auto_freebie_search_voucher_id', 'auto_benefits', ['voucher_id'], unique=False)
    op.create_index('ix_auto_freebie_search_variants', 'auto_benefits', ['variants'], unique=False)
    op.create_index('ix_auto_freebie_search_type', 'auto_benefits', ['type'], unique=False)
    op.create_index('ix_auto_freebie_search_to', 'auto_benefits', ['to'], unique=False)
    op.create_index('ix_auto_freebie_search_range_min', 'auto_benefits', ['range_min'], unique=False)
    op.create_index('ix_auto_freebie_search_range_max', 'auto_benefits', ['range_max'], unique=False)
    op.create_index('ix_auto_freebie_search_from', 'auto_benefits', ['from'], unique=False)
    op.create_index('ix_auto_freebie_search_cart_range_min', 'auto_benefits', ['cart_range_min'], unique=False)
    op.create_index('ix_auto_freebie_search_cart_range_max', 'auto_benefits', ['cart_range_max'], unique=False)
    ### end Alembic commands ###
