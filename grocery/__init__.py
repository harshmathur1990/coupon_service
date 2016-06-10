from flask import Blueprint

grocery_voucher_api = Blueprint('grocery_voucher_api/v1', __name__)

from api.v1 import couponapi, errors