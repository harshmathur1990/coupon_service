from datetime import datetime
import logging
from sqlalchemy import Table, MetaData, create_engine, exc, BINARY, ForeignKey,\
    VARCHAR, BOOLEAN, TIMESTAMP, Column,BIGINT, and_,or_, Enum, INTEGER
from sqlalchemy import asc, desc, select, exists
from config import DATABASE_URL
from enums import ItemType, UseType, BenefitType, FreebieEntityType, LocationType
from sqlalchemy.sql import func
logger = logging.getLogger()


class CouponsAlchemyDB:
    engine = None
    _table = dict()

    def __init__(self):
        self.conn = CouponsAlchemyDB.get_connection()

    def __del__(self):
        self.conn.close()

    @staticmethod
    def init():
        try:
            CouponsAlchemyDB.engine = create_engine(
                DATABASE_URL,
                paramstyle='format',
                isolation_level="REPEATABLE_READ",
                pool_recycle=3600,
                convert_unicode=True
            )

            metadata = MetaData()

            CouponsAlchemyDB.rule_table = Table(
                'rule', metadata,
                Column('id', BINARY(16), primary_key=True),
                Column('name', VARCHAR(255)),
                Column('description', VARCHAR(255)),
                Column('rule_type', INTEGER, nullable=False),
                Column('item_type', Enum(*ItemType)),
                Column('use_type', Enum(*UseType)),
                Column('no_of_uses_allowed_per_user', INTEGER),
                Column('no_of_total_uses_allowed', BIGINT),
                Column('range_min', INTEGER),
                Column('range_max', INTEGER),
                Column('amount_or_percentage', INTEGER),
                Column('max_discount_value', INTEGER),
                Column('location_type', Enum(*LocationType)),
                Column('benefit_type', Enum(*BenefitType)),
                Column('payment_specific', BOOLEAN, default=False),
                Column('active', BOOLEAN, default=False),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["rule"] = CouponsAlchemyDB.rule_table

            CouponsAlchemyDB.vouchers_table = Table(
                'vouchers', metadata,
                Column('code', VARCHAR(20), primary_key=True),
                Column('rule_id', BINARY(16), ForeignKey("rule.id"), nullable=False),
                Column('description', VARCHAR(255)),
                Column('from', TIMESTAMP),
                Column('to', TIMESTAMP),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["vouchers"] = CouponsAlchemyDB.vouchers_table

            CouponsAlchemyDB.freebie_value_list = Table(
                'freebie_value_list', metadata,
                Column('rule_id', BINARY(16), ForeignKey("rule.id"), primary_key=True),
                Column('entity_type', Enum(*FreebieEntityType), primary_key=True),
                Column('entity_id', BIGINT, primary_key=True, autoincrement=False),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["freebie_value_list"] = CouponsAlchemyDB.freebie_value_list

            CouponsAlchemyDB.item_type_value_list = Table(
                'item_type_value_list', metadata,
                Column('rule_id', BINARY(16), ForeignKey("rule.id"), primary_key=True),
                Column('item_id', BIGINT, primary_key=True, autoincrement=False),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["item_type_value_list"] = CouponsAlchemyDB.item_type_value_list

            CouponsAlchemyDB.location_value_list = Table(
                'location_value_list', metadata,
                Column('rule_id', BINARY(16), ForeignKey("rule.id"), primary_key=True),
                Column('location_id', BIGINT, primary_key=True, autoincrement=False),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["location_value_list"] = CouponsAlchemyDB.location_value_list

            CouponsAlchemyDB.payment_mode_list = Table(
                'payment_mode_list', metadata,
                Column('rule_id', BINARY(16), ForeignKey("rule.id"), primary_key=True),
                Column('payment_mode', VARCHAR(255), primary_key=True),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["payment_mode_list"] = CouponsAlchemyDB.payment_mode_list

            CouponsAlchemyDB.deleted_vouchers = Table(
                'deleted_vouchers', metadata,
                Column('id', BINARY(16), primary_key=True),
                Column('code', VARCHAR(20), nullable=False),
                Column('rule_id', BINARY(16), ForeignKey("rule.id"), nullable=False),
                Column('description', VARCHAR(255)),
                Column('from', TIMESTAMP),
                Column('to', TIMESTAMP),
                Column('created_by', BINARY(16), nullable=False),
                Column('updated_by', BINARY(16), nullable=False),
                Column('created_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('updated_at', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), onupdate=func.current_timestamp,
                       server_onupdate=func.current_timestamp(), nullable=False)
            )

            CouponsAlchemyDB._table["deleted_vouchers"] = CouponsAlchemyDB.deleted_vouchers

            CouponsAlchemyDB.voucher_use_tracker = Table(
                'voucher_use_tracker', metadata,
                Column('id', BINARY(16), primary_key=True),
                Column('user_id', BINARY(16), nullable=False),
                Column('applied_on', TIMESTAMP, default=func.current_timestamp,
                       server_default=func.current_timestamp(), nullable=False),
                Column('voucher_code', VARCHAR(20), ForeignKey("vouchers.code"), nullable=False),
                Column('order_id', BIGINT, nullable=False)
            )

            CouponsAlchemyDB._table["voucher_use_tracker"] = CouponsAlchemyDB.voucher_use_tracker

            metadata.create_all(CouponsAlchemyDB.engine)

        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)
        except Exception as err:
            logger.error(err, exc_info=True)

    @staticmethod
    def get_connection():
        return CouponsAlchemyDB.engine.connect()

    @staticmethod
    def get_raw_connection():
        return CouponsAlchemyDB.engine.raw_connection()

    @staticmethod
    def get_table(name):
        return CouponsAlchemyDB._table[name]

    def begin(self):
        self.trans = self.conn.begin()

    def commit(self):
        self.trans.commit()

    def rollback(self):
        self.trans.rollback()

    @staticmethod
    def args_to_where(table, args):
        clause = []
        for k, v in args.items():
            if isinstance(v, (list, tuple)):
                clause.append(table.c[k].in_(v))
            else:
                clause.append(table.c[k] == v)
        return and_(*clause)

    @staticmethod
    def args_to_where_or(table, args):
        clause = []
        for k, v in args.items():
            if isinstance(v, (list, tuple)):
                clause.append(table.c[k].in_(v))
            else:
                clause.append(table.c[k] == v)
        return or_(*clause)

    def insert_row(self, table_name, **values):
        table = CouponsAlchemyDB.get_table(table_name)
        insert = table.insert().values(values)
        self.conn.execute(insert)

    def insert_row_batch(self, table_name, values):
        table = CouponsAlchemyDB.get_table(table_name)
        self.conn.execute(table.insert(), values)

    def update_row(self,table_name,*keys, **row):
        table = CouponsAlchemyDB.get_table(table_name)
        try:
            if not isinstance(keys, (list, tuple)):
                keys = [keys]
            if not keys or len(keys) == len(row):
                return False
            clause = dict()
            for k in keys:
                clause[k] = row[k]
            clean_row = row.copy()
            for key in keys:
                if key in clean_row.keys():
                    del clean_row[key]
            clauses = CouponsAlchemyDB.args_to_where(table, clause)
            update = table.update(clauses, clean_row)
            self.conn.execute(update)
            return True
        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)(err, True)
            return False

    def update_row_new(self, table_name, where=None, val=None):
        if not where:
            where = {}
        if not val:
            val = {}
        try:
            table = CouponsAlchemyDB.get_table(table_name)
            clauses = CouponsAlchemyDB.args_to_where(table, where)
            update = table.update(clauses, val)
            self.conn.execute(update)
            return True
        except Exception as err:
            logger.error(err, exc_info=True)(err, True)
            return False

    def delete_row(self, table_name, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        try:
            delete = table.delete().where(CouponsAlchemyDB.args_to_where(table, where))
            self.conn.execute(delete)
        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)(err, True)
            return False

    def find_one(self,table_name, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        sel = select([table]).where(CouponsAlchemyDB.args_to_where(table, where))
        row = self.conn.execute(sel)
        tup = row.fetchone()
        if tup:
            return dict(tup)
        return False

    def exists_row(self, table_name, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        try:
            sel = select([table]).where(CouponsAlchemyDB.args_to_where(table, where))
            sel = select([exists(sel)])
            row = self.conn.execute(sel).scalar()
            if row:
                return True
        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)
        return False

    def find(self, table_name, order_by="id", _limit=None, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        try:
            func = asc
            if order_by and order_by.startswith('_'):
                order_by = order_by[1:]
                func = desc
            if _limit:
                sel = select([table]).where(CouponsAlchemyDB.args_to_where(table, where)).order_by(func(order_by)).limit(_limit)
            else:
                sel = select([table]).where(CouponsAlchemyDB.args_to_where(table, where)).order_by(func(order_by))
            row = self.conn.execute(sel)
            tup = row.fetchall()
            l = [dict(r) for r in tup]
            return l
        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)
            return False

    def find_or(self, table_name, order_by="id", _limit=None, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        try:
            func = asc
            if order_by and order_by.startswith('_'):
                order_by = order_by[1:]
                func = desc
            if _limit:
                sel = select([table]).where(CouponsAlchemyDB.args_to_where_or(table, where)).order_by(func(order_by)).limit(_limit)
            else:
                sel = select([table]).where(CouponsAlchemyDB.args_to_where_or(table, where)).order_by(func(order_by))
            row = self.conn.execute(sel)
            tup = row.fetchall()
            l = [dict(r) for r in tup]
            return l
        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)
            return False

    @staticmethod
    def args_to_join(table1, table2, args):
        clause = []
        for k, v in args.items():
            clause.append(table1.c[k] == table2.c[v])
        return and_(*clause)

    def select_outer_join(self, table_names, foreign_key, where):
        table = [CouponsAlchemyDB.get_table(t) for t in table_names]
        try:
            fclause = CouponsAlchemyDB.args_to_join(table[0], table[1], foreign_key[0])
            logger.debug(fclause)
            clause = CouponsAlchemyDB.args_to_where_join(where)
            logger.debug(clause)
            # clause = and_(fclause,clause)
            logger.debug(clause)
            j = table[0].outerjoin(table[1], fclause)
            for i in range(1, len(foreign_key)):
                fclause = CouponsAlchemyDB.args_to_join(table[i], table[i+1], foreign_key[i])
                j = j.join(table[i+1], fclause)
            sel = select(table, use_labels=True).select_from(j).where(clause)
            row = self.conn.execute(sel)
            tup = row.fetchall()
            l = [dict(r) for r in tup]
            return l
        except Exception as e:
            logger.exception(e)
            return False

    @staticmethod
    def args_to_where_join(where):
        # where = [({"SocialContact.Email": email}), ({"AppUserId": appid})]
        logger.debug(where)
        or_list = []
        for tup in where:
            and_list = []
            for r in tup:
                if r:
                    logger.debug(r)
                    tab, col = r.keys()[0].split('.')
                    table = CouponsAlchemyDB.get_table(tab)
                    v = r.values()[0]
                    if isinstance(v, (list, tuple)):
                        and_list.append(table.c[col].in_(v))
                    else:
                        and_list.append(table.c[col] == v)
                or_list.append(and_(*and_list))
        return or_(*or_list)