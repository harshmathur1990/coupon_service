from api import rule_api, voucher_api
from flask import Flask
from lib import log
from lib.converters import HexConverter
from src.sqlalchemydb import CouponsAlchemyDB


def create_app():
    app = Flask(__name__)
    app.url_map.converters['hex'] = HexConverter
    app.register_blueprint(rule_api, url_prefix='/rules')
    app.register_blueprint(voucher_api, url_prefix='/vouchers/v1')
    log.setup_logging()
    CouponsAlchemyDB.init()
    return app