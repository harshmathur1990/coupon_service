from flask import Blueprint

rule_api = Blueprint('rule_api', __name__)
voucher_api = Blueprint('voucher_api', __name__)
from . import voucherapi, ruleapi, errors
