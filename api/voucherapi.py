from webargs import fields, validate
from flask import request
from webargs.flaskparser import parser
from lib.decorator import jsonify
from src.rules.validate import validate_for_create_voucher, create_voucher_object
from . import rule_api


@rule_api.route('/<hex:rule_id>/vouchers', methods=['POST'])
@jsonify
def create_voucher(rule_id):
    voucher_create_args = {
        'description': fields.Str(required=False, missing=None, location='json'),
        'code': fields.List(fields.Str(), required=True, location='json'),
        'from': fields.DateTime(required=True, location='json'),
        'to': fields.DateTime(required=True, location='json'),
        'user_id': fields.Str(required=True, location='json')
    }
    args = parser.parse(voucher_create_args, request)
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
