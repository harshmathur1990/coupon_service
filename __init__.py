from api import rule_api, voucher_api, voucher_api_v_1_1
from grocery import grocery_voucher_api
from config import client
from flask import Flask
from lib import log
from lib.converters import HexConverter, ListConverter
from src.sqlalchemydb import CouponsAlchemyDB


def create_app():
    app = Flask(__name__)
    app.url_map.converters['hex'] = HexConverter
    app.url_map.converters['list'] = ListConverter
    if client == 'new_grocery':
        app.register_blueprint(grocery_voucher_api, url_prefix='/vouchers/grocery')
    else:
        app.register_blueprint(rule_api, url_prefix='/rules')
        app.register_blueprint(voucher_api, url_prefix='/vouchers/v1')
        app.register_blueprint(voucher_api_v_1_1, url_prefix='/vouchers/v1.1')
    log.setup_logging()
    CouponsAlchemyDB.init()
    return app
