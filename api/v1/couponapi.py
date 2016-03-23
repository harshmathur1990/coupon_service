from flask import request
from lib.decorator import jsonify
from lib.utils import is_timezone_aware
from src.enums import *
from src.rules.vouchers import VoucherTransactionLog
from src.rules.utils import get_benefits, apply_benefits, create_and_save_rule_list, save_vouchers
from src.rules.validate import validate_coupon, validate_for_create_coupon,\
    validate_for_create_voucher
from webargs import fields, validate
from webargs.flaskparser import parser
from api import voucher_api
from validate import validate_for_create_api_v1
from utils import create_freebie_coupon


@voucher_api.route('/apply', methods=['POST'])
@jsonify
def apply_coupon():
    apply_coupon_args = {
        'order_id': fields.Str(required=True, location='json'),

        'customer_id': fields.Str(required=True, location='json'),

        'area_id': fields.Int(required=True, location='json'),

        'products': fields.List(
            fields.Nested(
                {
                    'item_id': fields.Int(validate=validate.Range(min=0), required=True),
                    'quantity': fields.Int(validate=validate.Range(min=1), required=True),
                    'coupon_codes': fields.List(
                        fields.Str(),
                        required=False
                    )
                }
            ),
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
    success, order, error = validate_coupon(args)
    if success:
        # coupon is valid, try applying it
        benefits = get_benefits(order)
        benefits_applied = apply_benefits(args, order)
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
            'paymentModes': [],
            'message': error
        }


@voucher_api.route('/check', methods=['POST'])
@jsonify
def check_coupon():
    check_coupon_args = {

        'customer_id': fields.Str(required=True, location='json'),

        'area_id': fields.Int(required=True, location='json'),

        'products': fields.List(
            fields.Nested(
                {
                    'item_id': fields.Int(validate=validate.Range(min=0), required=True),
                    'quantity': fields.Int(validate=validate.Range(min=1), required=True),
                    'coupon_codes': fields.List(
                        fields.Str(),
                        required=False
                    )
                }
            ),
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
    args = parser.parse(check_coupon_args, request)
    success, order, error = validate_coupon(args)
    if success:
        # coupon is valid, try applying it
        benefits = get_benefits(order)
        benefits['success'] = True
        return benefits
    return {
        'success': False,
        'error': {
            'code': 400
        },
        'products': [],
        'freebies': [],
        'totalDiscount': 0.0,
        'channel': [],
        'paymentModes': [],
        'message': error
    }


@voucher_api.route('/create', methods=['POST'])
@jsonify
def create_voucher():
    coupon_create_args = {
        'name': fields.Str(required=False, missing=None, location='json'),

        'description': fields.Str(required=False, missing=None, location='json'),

        'type': fields.Int(required=False, missing=RuleType.regular_coupon.value,
                           location='json', validate=validate.OneOf(
                [l.value for l in list(RuleType)], [l.name for l in list(RuleType)])),

        'user_id': fields.Str(required=False),

        'code': fields.List(fields.Str(), required=True, location='json'),

        'from': fields.DateTime(required=True, location='json'),

        'to': fields.DateTime(required=True, location='json'),

        'rules': fields.List(
            fields.Nested(
                {
                    'description': fields.Str(required=False),

                    'criteria': fields.Nested({
                        'no_of_uses_allowed_per_user': fields.Int(required=False, missing=None,
                                                          validate=validate.Range(min=0)),

                        'no_of_total_uses_allowed': fields.Int(required=False, missing=None,
                                                               validate=validate.Range(min=0)),

                        'range_min': fields.Int(required=False, missing=None,
                                                validate=validate.Range(min=0)),

                        'range_max': fields.Int(required=False, missing=None,
                                                validate=validate.Range(min=0)),

                        "cart_range_min": fields.Int(required=False, missing=None,
                                                     validate=validate.Range(min=0)),

                        "cart_range_max": fields.Int(required=False, missing=None,
                                                     validate=validate.Range(min=0)),

                        'channels': fields.List(
                            fields.Int(
                                validate=validate.OneOf(
                                    [l.value for l in list(Channels)], [l.name for l in list(Channels)])),
                            required=False,
                            missing=list()
                        ),

                        'brands': fields.List(
                            fields.Int(
                                validate=validate.Range(min=0)
                            ),
                            required=False,
                            missing=list()
                        ),

                        'products': fields.List(
                            fields.Int(
                                validate=validate.Range(min=0)
                            ),
                            required=False,
                            missing=list()
                        ),

                        'categories': fields.Nested(
                            {
                                'in': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ),
                                    required=False,
                                    missing=list(),
                                ),
                                'not_in': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ),
                                    required=False,
                                    missing=list(),
                                )
                            },
                            required=False,
                            missing={'in': [], 'not_in': []}
                        ),

                        'storefronts': fields.List(
                            fields.Int(
                                validate=validate.Range(min=0)
                            ),
                            required=False,
                            missing=list()
                        ),

                        'variants': fields.List(
                            fields.Int(
                                validate=validate.Range(min=0)
                            ),
                            required=False,
                            missing=list()
                        ),

                        'sellers': fields.List(
                            fields.Int(
                                validate=validate.Range(min=0)
                            ),
                            required=False,
                            missing=list()
                        ),

                        'location': fields.Nested(
                            {
                                'country': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ),
                                ),
                                'state': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ),
                                ),
                                'city': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ),
                                ),
                                'area': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ),
                                ),
                                'zone': fields.List(
                                    fields.Int(),
                                ),
                            },
                            required=False,
                            missing={'country': [], 'state': [], 'city': [], 'area': [], 'zone': []}
                        ),

                        'payment_modes': fields.List(
                            fields.Str(),
                            missing=list(),
                            required=False
                        ),

                        'valid_on_order_no': fields.List(
                            fields.Str(),
                            required=False,
                            missing=list()
                        ),
                    }),

                    'benefits': fields.Nested({
                        'freebies': fields.List(
                            fields.List(
                                fields.Int(
                                validate=validate.Range(min=0)
                                ),
                            ),
                            required=False,
                            missing=list()
                        ),

                        'amount': fields.Int(
                            required=False, missing=None, validate=validate.Range(min=0)
                        ),

                        'percentage': fields.Int(
                            required=False, missing=None, validate=validate.Range(min=0, max=100)
                        ),

                        'max_discount': fields.Int(
                            required=False, validate=validate.Range(min=0)
                        )
                    })
                }
            ),
            missing = list(),
            location='json'
        )

    }
    args = parser.parse(coupon_create_args, request)

    # api specific validation
    success, error = validate_for_create_api_v1(args)
    if not success:
        rv = {
            'success': success,
            'error': {
                'code': 400,
                'error': error
            }
        }
        return rv

    # general validations
    success, error = validate_for_create_coupon(args)

    if not success:
        rv = {
            'success': success,
            'error': {
                'code': 400,
                'error': error
            }
        }
        return rv

    if args.get('type') is RuleType.regular_coupon.value:
        rule_id_list, rule_list = create_and_save_rule_list(args)
        if not rule_id_list:
            rv = {
                'success': False,
                'error': {
                    'code': 400,
                    'error': u'Unknown Exception'
                }
            }
            return rv

        if is_timezone_aware(args.get('from')):
            args['from'] = args.get('from').replace(tzinfo=None)

        if is_timezone_aware(args.get('to')):
            args['to'] = args.get('to').replace(tzinfo=None)

        success, error = validate_for_create_voucher(args)
        if not success:
            rv = {
                'success': success,
                'error': {
                    'code': 400,
                    'error': error
                }
            }
            return rv

        success_list, error_list = save_vouchers(args, rule_id_list)

        rv = {
            'success': True,
            'data': {
                'success_list': success_list,
                'error_list': error_list
            }
        }
        return rv
    else:
        success, data, error = create_freebie_coupon(args)
        if not success:
            rv = {
                'success': success,
                'error': {
                    'code': 400,
                    'error': error
                }
            }
            return rv
        rv = {
            'success': True,
            'data': {
                'success_list': data,
                'error_list': error
            }
        }
        return rv


@voucher_api.route('/confirm', methods=['POST'])
@jsonify
def confirm_order():
    confirm_order_args = {
        'order_id': fields.Str(required=True, location='json'),
        'payment_status': fields.Bool(required=True, location='json')
    }
    args = parser.parse(confirm_order_args, request)
    success, error = VoucherTransactionLog.make_transaction_log_entry(args)
    rv = {
        'success': success,
    }
    if not success:
        rv['error'] = {
            'code': 400,
            'error': error
        }
    return rv
