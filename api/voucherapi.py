import pytz
from pytz import timezone
from webargs import fields
from flask import request
from webargs.flaskparser import parser
from lib.decorator import jsonify
from src.rules.validate import validate_for_create_voucher, create_voucher_object
from . import rule_api
from lib.utils import is_timezone_aware

# if a timezone is not present in any input datetime, we will assume IST
IN = timezone("Asia/Kolkata")

@rule_api.route('/<hex:rule_id>/vouchers', methods=['POST'])
@jsonify
def create_voucher(rule_id):
    # It is mandatory that from and to are in UTC.
    voucher_create_args = {
        'description': fields.Str(required=False, missing=None, location='json'),
        'code': fields.List(fields.Str(), required=True, location='json'),
        'from': fields.DateTime(required=True, location='json'),
        'to': fields.DateTime(required=True, location='json'),
        'user_id': fields.Str(required=True, location='json')
    }
    args = parser.parse(voucher_create_args, request)

    if is_timezone_aware(args.get('from')):
        args['from'] = args.get('from').replace(tzinfo=None)

    if not is_timezone_aware(args.get('to')):
        args['to'] = args.get('to').replace(tzinfo=None)

    success, error = validate_for_create_voucher(args, rule_id)
    if not success:
        rv = {
            'success': success,
            'error': {
                'code': 400,
                'error': error
            }
        }
        return rv
    code_list = args.get('code')
    success_list = list()
    error_list = list()
    for code in code_list:
        voucher = create_voucher_object(args, rule_id, code)
        success = voucher.save()
        if success:
            success_list.append(success)
        else:
            error = {
                'code': code,
                'reason': u'{} already exists'.format(code)
            }
            error_list.append(error)
    rv = {
        'success': True,
        'data': {
            'success_list': success_list,
            'error_list': error_list
        }
    }
    return rv
