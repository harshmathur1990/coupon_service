from sqlalchemy import create_engine, MetaData

engine = create_engine(
    'mysql+pymysql://root:root@localhost/coupons',
    convert_unicode=True)

metadata = MetaData()
