from datetime import datetime
import logging
from sqlalchemy import Table, MetaData, create_engine, exc, BINARY, ForeignKey,\
    VARCHAR, BOOLEAN, Column, and_, or_, Index, TEXT
from sqlalchemy.dialects.mysql import TINYINT, INTEGER, BIGINT, DATETIME
from sqlalchemy import asc, desc, select, exists
from config import DATABASE_URL, client
from sqlalchemy.sql import text
logger = logging.getLogger()



class CouponsAlchemyDB:
    engine = None
    _table = dict()
    metadata = None

    def __init__(self):
        self.conn = CouponsAlchemyDB.get_connection()

    def __del__(self):
        self.conn.close()

    @staticmethod
    def init():
        try:
            from lib.utils import get_agent_id
            CouponsAlchemyDB.engine = create_engine(
                DATABASE_URL,
                paramstyle='format',
                pool_recycle=3600,
                isolation_level='REPEATABLE_READ',
                convert_unicode=True
            )

            CouponsAlchemyDB.metadata = MetaData()

            CouponsAlchemyDB.tokens = Table(
                'tokens', CouponsAlchemyDB.metadata,
                Column('token', VARCHAR(250), primary_key=True),
                Column('agent_id', INTEGER, index=True, unique=True, nullable=False),
                Column('agent_name', VARCHAR(250), unique=True, index=True, nullable=False),
                Column('created_at', DATETIME(fsp=6)),
                Column('last_accessed_at', DATETIME(fsp=6)),
            )

            CouponsAlchemyDB._table["tokens"] = CouponsAlchemyDB.tokens

            CouponsAlchemyDB.rule_table = Table(
                'rule', CouponsAlchemyDB.metadata,
                Column('id', BINARY(16), primary_key=True),
                Column('name', VARCHAR(255)),
                Column('description', VARCHAR(255)),
                Column('criteria_json', VARCHAR(2000), nullable=False),
                Column('blacklist_criteria_json', VARCHAR(2000), nullable=True),
                Column('benefits_json', VARCHAR(1000), nullable=False),
                Column('sha2hash', VARCHAR(64), index=True),
                Column('active', BOOLEAN, default=False),
                Column('created_by', VARCHAR(32), nullable=False, default=''),
                Column('updated_by', VARCHAR(32), nullable=False, default=''),
                Column('created_at', DATETIME(fsp=6), default=datetime.utcnow, nullable=False),
                Column('updated_at', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow),
                Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True)
            )

            CouponsAlchemyDB._table["rule"] = CouponsAlchemyDB.rule_table

            CouponsAlchemyDB.vouchers_table = Table(
                'vouchers', CouponsAlchemyDB.metadata,
                Column('id', BINARY(16), unique=True, nullable=False),
                Column('code', VARCHAR(200), primary_key=True),
                Column('rules', VARCHAR(150), nullable=False),
                Column('custom', VARCHAR(1000)),
                Column('description', VARCHAR(255)),
                Column('from', DATETIME(fsp=6)),
                Column('to', DATETIME(fsp=6)),
                Column('schedule', VARCHAR(250)),
                Column('mutable', BOOLEAN, default=False),
                Column('type', TINYINT(unsigned=True), nullable=False),
                Column('created_by', VARCHAR(32), nullable=False, default=''),
                Column('updated_by', VARCHAR(32), nullable=False, default=''),
                Column('created_at', DATETIME(fsp=6), default=datetime.utcnow, nullable=False),
                Column('updated_at', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow),
                Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True)
            )

            CouponsAlchemyDB._table["vouchers"] = CouponsAlchemyDB.vouchers_table

            CouponsAlchemyDB.all_vouchers = Table(
                'all_vouchers', CouponsAlchemyDB.metadata,
                Column('id', BINARY(16), primary_key=True),
                Column('code', VARCHAR(200), index=True, nullable=False),
                Column('rules', VARCHAR(150), nullable=False),
                Column('custom', VARCHAR(1000)),
                Column('description', VARCHAR(255)),
                Column('from', DATETIME(fsp=6)),
                Column('to', DATETIME(fsp=6)),
                Column('schedule', VARCHAR(250)),
                Column('mutable', BOOLEAN, default=False),
                Column('type', TINYINT(unsigned=True), nullable=False),
                Column('created_by', VARCHAR(32), nullable=False, default=''),
                Column('updated_by', VARCHAR(32), nullable=False, default=''),
                Column('created_at', DATETIME(fsp=6), default=datetime.utcnow, nullable=False),
                Column('updated_at', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, onupdate=datetime.utcnow),
                Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True)
            )

            CouponsAlchemyDB._table["all_vouchers"] = CouponsAlchemyDB.all_vouchers

            CouponsAlchemyDB.voucher_use_tracker = Table(
                'voucher_use_tracker', CouponsAlchemyDB.metadata,
                Column('id', BINARY(16), primary_key=True),   # COMM: auto-increment?
                Column('user_id', VARCHAR(32), nullable=False),
                Column('applied_on', DATETIME(fsp=6), default=datetime.utcnow, nullable=False),
                Column('voucher_id', BINARY(16), ForeignKey("all_vouchers.id"), nullable=False),
                Column('order_id', VARCHAR(32), nullable=False),
                Column('response', VARCHAR(8000)),
                Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True),
                Index("voucher_use_tracker_user_id", "user_id"),
                Index("voucher_use_tracker_voucher_id", "voucher_id"),
                Index("voucher_use_tracker_user_id_voucher_id", "user_id", "voucher_id")
            )

            CouponsAlchemyDB._table["voucher_use_tracker"] = CouponsAlchemyDB.voucher_use_tracker

            CouponsAlchemyDB.user_voucher_transaction_log = Table(
                'user_voucher_transaction_log', CouponsAlchemyDB.metadata,
                Column('id', BINARY(16), primary_key=True),  # COMM: auto-increment?
                Column('user_id', VARCHAR(32), nullable=False),
                Column('updated_on', DATETIME(fsp=6), default=datetime.utcnow, nullable=False),
                Column('voucher_id', BINARY(16), ForeignKey("all_vouchers.id"), nullable=False),
                Column('order_id', VARCHAR(32), nullable=False),
                Column('status', TINYINT(unsigned=True), nullable=False),
                Column('response', VARCHAR(8000)),
                Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True),
                Index("user_voucher_transaction_log_user_id", "user_id"),
                Index("user_voucher_transaction_log_voucher_id", "voucher_id"),
                Index("user_voucher_transaction_log_user_id_voucher_id", "user_id", "voucher_id")
            )

            CouponsAlchemyDB._table["user_voucher_transaction_log"] = CouponsAlchemyDB.user_voucher_transaction_log

            if client == 'grocery':
                CouponsAlchemyDB.auto_benefits = Table(
                    'auto_benefits', CouponsAlchemyDB.metadata,
                    Column('id', BIGINT, primary_key=True, autoincrement=True),
                    Column('type', INTEGER, index=True, nullable=False),
                    Column('variants', INTEGER, index=True),
                    Column('zone', INTEGER, index=True, nullable=False),
                    Column('range_min', INTEGER, index=True),
                    Column('range_max', INTEGER, index=True),
                    Column('cart_range_min', INTEGER, index=True),
                    Column('cart_range_max', INTEGER, index=True),
                    Column('voucher_id', BINARY(16), ForeignKey("all_vouchers.id"), nullable=False, index=True),
                    Column('from', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, index=True),
                    Column('to', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, index=True),
                    Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True)
                )

                CouponsAlchemyDB._table["auto_benefits"] = CouponsAlchemyDB.auto_benefits

            elif client == 'new_grocery':
                CouponsAlchemyDB.auto_benefits = Table(
                    'auto_benefits', CouponsAlchemyDB.metadata,
                    Column('id', BIGINT, primary_key=True, autoincrement=True),
                    Column('type', INTEGER, index=True, nullable=False),
                    Column('variants', INTEGER, index=True),
                    Column('zone', INTEGER, index=True, nullable=False),
                    Column('range_min', INTEGER, index=True),
                    Column('range_max', INTEGER, index=True),
                    Column('cart_range_min', INTEGER, index=True),
                    Column('cart_range_max', INTEGER, index=True),
                    Column('voucher_id', BINARY(16), ForeignKey("all_vouchers.id"), nullable=False, index=True),
                    Column('from', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, index=True),
                    Column('to', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, index=True),
                    Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True)
                )

                CouponsAlchemyDB._table["auto_benefits"] = CouponsAlchemyDB.auto_benefits

            elif client == 'pay':
                CouponsAlchemyDB.auto_benefits = Table(
                    'auto_benefits', CouponsAlchemyDB.metadata,
                    Column('id', BIGINT, primary_key=True, autoincrement=True),
                    Column('type', INTEGER, index=True, nullable=False),
                    Column('variants', INTEGER, index=True),
                    Column('zone', INTEGER, index=True, nullable=False),
                    Column('range_min', INTEGER, index=True),
                    Column('range_max', INTEGER, index=True),
                    Column('cart_range_min', INTEGER, index=True),
                    Column('cart_range_max', INTEGER, index=True),
                    Column('voucher_id', BINARY(16), ForeignKey("all_vouchers.id"), nullable=False, index=True),
                    Column('from', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, index=True),
                    Column('to', DATETIME(fsp=6), default=datetime.utcnow, nullable=False, index=True),
                    Column('agent_id', INTEGER, ForeignKey("tokens.agent_id"), default=get_agent_id, nullable=True)
                )

                CouponsAlchemyDB._table["auto_benefits"] = CouponsAlchemyDB.auto_benefits

            CouponsAlchemyDB.auto_tester = Table(
                'auto_tester', CouponsAlchemyDB.metadata,
                Column('id', BIGINT, primary_key=True, autoincrement=True),
                Column('url', VARCHAR(250), nullable=False),
                Column('params', VARCHAR(100), nullable=True),
                Column('body', TEXT, nullable=False),
                Column('prod_response', TEXT, nullable=False),
                Column('staging_response', TEXT, nullable=False),
                Column('match', TINYINT(unsigned=True), nullable=False),
                Column('updated_on', DATETIME(fsp=6), default=datetime.utcnow, nullable=False),
            )

            CouponsAlchemyDB._table["auto_tester"] = CouponsAlchemyDB.auto_tester
            # no need of below statement. DB can be created by upgrade with initial migration script.
            # But if we retain the below statement, then the database gets created before migration can
            # check the difference between metadata model and the actual database,
            # and hence will find no difference and will create empty migration script
            #CouponsAlchemyDB.metadata.create_all(CouponsAlchemyDB.engine)

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

    def update_row(self, table_name, *keys, **row):
        table = CouponsAlchemyDB.get_table(table_name)
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

    def delete_row_in_transaction(self, table_name, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        delete = table.delete().where(CouponsAlchemyDB.args_to_where(table, where))
        self.conn.execute(delete)

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

    def count(self, table_name, **where):
        table = CouponsAlchemyDB.get_table(table_name)
        try:
            sel = select([table.c.id]).where(CouponsAlchemyDB.args_to_where(table, where))
            row = self.conn.execute(sel)
            count = row.rowcount
            return count
        except exc.SQLAlchemyError as err:
            logger.error(err, exc_info=True)
            return False

    def execute_raw_sql(self, sql, kwargs):
        try:
            row = self.conn.execute(text(sql), kwargs)
            tup = row.fetchall()
            l = [dict(r) for r in tup]
            return l
        except Exception as e:
            logger.exception(e)
            return False
