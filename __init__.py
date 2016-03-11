from flask import Flask

from api import api
from lib import log
from src.sqlalchemydb import CouponsAlchemyDB


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api)
    log.setup_logging()
    CouponsAlchemyDB.init()
    return app