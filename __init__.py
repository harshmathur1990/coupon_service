from flask import Flask

from api import api
from lib import log
from src.sqlalchemydb import CouponsAlchemyDB
from api.converters import HexConverter


def create_app():
    app = Flask(__name__)
    app.url_map.converters['hex'] = HexConverter
    app.register_blueprint(api)
    log.setup_logging()
    CouponsAlchemyDB.init()
    return app