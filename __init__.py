from flask import Flask
from src import log
from src.sqlalchemydb import CouponsAlchemyDB


def create_app():
    app = Flask(__name__)
    log.setup_logging()
    CouponsAlchemyDB.init()
    return app