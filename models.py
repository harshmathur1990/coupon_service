from sqlalchemy import Table, Column, Integer, LargeBinary,\
    Unicode, BigInteger, Boolean, TIMESTAMP, ForeignKey
from database import metadata


rule = Table(
    'rule', metadata,
    Column('id', LargeBinary(16), primary_key=True),
    Column('name', Unicode(255)),
    Column('description', Unicode(255)),
    Column('rule_type', Integer),
    Column('item_type', Integer),
    Column('use_type', Integer),
    Column('no_of_uses_allowed_per_user', Integer),
    Column('no_of_total_uses_allowed', BigInteger),
    Column('range_min', Integer),
    Column('range_max', Integer),
    Column('amount_or_percentage', Integer),
    Column('max_discount_value', Integer),
    Column('location_type', Integer),
    Column('benefit_type', Integer),
    Column('payment_specific', Integer),
    Column('active', Boolean),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


vouchers = Table(
    'vouchers', metadata,
    Column('code', Unicode(20), primary_key=True),
    Column('rule_id', LargeBinary(16), ForeignKey("rule.id"), nullable=False),
    Column('description', Unicode(255)),
    Column('from', TIMESTAMP),
    Column('to', TIMESTAMP),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


freebie_value_list = Table(
    'freebie_value_list', metadata,
    Column('rule_id', LargeBinary(16), ForeignKey("rule.id"), primary_key=True),
    Column('entity_type', Integer, primary_key=True),
    Column('entity_id', BigInteger, primary_key=True),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


item_type_value_list = Table(
    'item_type_value_list', metadata,
    Column('rule_id', LargeBinary(16), ForeignKey("rule.id"), primary_key=True),
    Column('item_id', BigInteger, primary_key=True),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


location_value_list = Table(
    'location_value_list', metadata,
    Column('rule_id', LargeBinary(16), ForeignKey("rule.id"), primary_key=True),
    Column('location_id', BigInteger, primary_key=True),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


payment_mode_list = Table(
    'payment_mode_list', metadata,
    Column('rule_id', LargeBinary(16), ForeignKey("rule.id"), primary_key=True),
    Column('payment_mode', Unicode(255), primary_key=True),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


deleted_vouchers = Table(
    'deleted_vouchers', metadata,
    Column('id', LargeBinary(16), primary_key=True),
    Column('code', Unicode(20)),
    Column('rule_id', LargeBinary(16), ForeignKey("rule.id"), nullable=False),
    Column('description', Unicode(255)),
    Column('from', TIMESTAMP),
    Column('to', TIMESTAMP),
    Column('created_by', LargeBinary(16)),
    Column('updated_by', LargeBinary(16)),
    Column('created_at', TIMESTAMP),
    Column('updated_at', TIMESTAMP)
)


voucher_use_tracker = Table(
    'voucher_use_tracker', metadata,
    Column('id', LargeBinary(16), primary_key=True),
    Column('user_id', LargeBinary(16)),
    Column('applied_on', TIMESTAMP),
    Column('voucher_code', Unicode(20), ForeignKey("vouchers.code"), nullable=False),
    Column('order_id', BigInteger, nullable=False)
)
