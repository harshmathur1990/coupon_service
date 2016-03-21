from flask import Blueprint

rule_api = Blueprint('rule_api/v1', __name__)
voucher_api = Blueprint('voucher_api/v1', __name__)
import src
from api.v1 import ruleapi
