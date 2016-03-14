from webargs import fields, validate
from src.enums import *
from . import voucher_api
from flask import request
from webargs.flaskparser import parser
from lib.decorator import jsonify
from src.rules.validate import validate_coupon
from src.rules.utils import get_benefits, apply_benefits


@voucher_api.route('/apply', methods=['POST'])
@jsonify
def apply_coupon():
    apply_coupon_args = {
        'order_id': fields.Str(required=True, location='json'),

        'customer_id': fields.Str(required=True, location='json'),

        'zone_code': fields.Str(required=False, location='json'),

        'products': fields.Nested(
            {
                'item_id': fields.Int(validate=validate.Range(min=0), required=True),
                'quantity': fields.Int(validate=validate.Range(min=1), required=True),
                'coupon_codes': fields.List(
                    fields.Str(),
                    required=True
                )
            },
            required=True,
            location='json'
        ),

        'coupon_codes': fields.List(
            fields.Str(),
            location='json',
            required=True
        ),

        'freebies': fields.List(
            fields.Int(),
            required=False,
            location='json',
            missing=list()
        ),

        'channel': fields.List(
            fields.Int(validate=validate.OneOf([l.value for l in list(Channels)], [l.name for l in list(Channels)])),
            required=True,
            location='json'
        )
    }
    args = parser.parse(apply_coupon_args, request)
    success, data, error = validate_coupon(args)
    if success:
        # coupon is valid, try applying it
        benefits = get_benefits(data)
        benefits_applied = apply_benefits(args, benefits)
        if not benefits_applied:
            err = {
                'success': False,
                'error': {
                    'code': 500,
                    'error': 'Internal Server error'
                }
            }
            return err
        benefits['success'] = True
        return benefits
    else:
       return {
           'success': False,
           'error': {
               'code': 400
           },
           'products': [],
           'freebies': [],
           'totalDiscount': 0.0,
           'channel': [],
           'paymentModes': []
       }

