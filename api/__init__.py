from flask import Blueprint

rule_api = Blueprint('rule_api/v1', __name__)
voucher_api = Blueprint('voucher_api/v1', __name__)
voucher_api_v_1_1 = Blueprint('voucher_api/v1.1', __name__)
from api.v1 import couponapi, errors
