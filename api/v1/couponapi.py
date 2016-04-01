from flask import request
from lib.decorator import jsonify, check_login
from lib.utils import is_timezone_aware, create_error_response, create_success_response
from src.enums import *
from src.rules.vouchers import VoucherTransactionLog, Vouchers
from src.rules.utils import get_benefits, apply_benefits, create_and_save_rule_list, save_vouchers, fetch_auto_benefits
from src.rules.validate import validate_coupon, validate_for_create_coupon,\
    validate_for_create_voucher
from webargs import fields, validate
from webargs.flaskparser import parser
from api import voucher_api
from validate import validate_for_create_api_v1
from utils import create_freebie_coupon


@voucher_api.route('/apply', methods=['POST'])
@jsonify
@check_login
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
    success, order, error = validate_coupon(args, validate_for_apply=True)
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
        benefits['errors'] = error
        return benefits
    else:
        return {
            'success': False,
            'error': {
                'code': 400,
                'error': ','.join(error)
            },
            'products': [],
            'freebies': [],
            'totalDiscount': 0.0,
            'channel': [],
            'paymentModes': [],
            'errors': error
        }


@voucher_api.route('/check', methods=['POST'])
@jsonify
@check_login
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
            required=False,
            missing=list()
        ),

        'benefits': fields.List(
            fields.Nested(
                {
                    'items': fields.List(fields.Int, required=True),
                    'couponCode': fields.Str(required=True),
                    'freebies': fields.List(fields.Int, required=False),
                    'discount': fields.Float(validate=validate.Range(min=0), required=False),
                    'type': fields.Int(
                        validate=validate.OneOf(
                            [l.value for l in list(VoucherType)], [l.name for l in list(VoucherType)]),
                        required=True),
                    'paymentMode': fields.List(fields.Int, required=False),
                    'channel': fields.Int(
                        validate=validate.OneOf([l.value for l in list(Channels)], [l.name for l in list(Channels)]),
                        required=False)
                }
            ),
            required=False,
            location='json'
        ),

        'channel': fields.Int(
            validate=validate.OneOf([l.value for l in list(Channels)], [l.name for l in list(Channels)]),
            required=True,
            location='json'
            ),

        'order_id': fields.Str(required=False, location='json'),

    }
    args = parser.parse(check_coupon_args, request)
    success, order, error = validate_coupon(args)
    if success and not order.existing_vouchers:
        fetch_auto_benefits(order, VoucherType.regular_freebie)
    if order:
        fetch_auto_benefits(order, VoucherType.auto_freebie)
    benefits = get_benefits(order)

    if success:
        # coupon is valid, try applying it
        benefits['success'] = True
        benefits['errors'] = error
        return benefits
    return {
        'success': False,
        'error': {
            'code': 400,
            'error': ','.join(error)
        },
        'products': [],
        'freebies': [],
        'totalDiscount': 0.0,
        'channel': [],
        'paymentModes': [],
        'errors': error
    }


@voucher_api.route('/create', methods=['POST'])
@jsonify
@check_login
def create_voucher():
    coupon_create_args = {
        'name': fields.Str(required=False, missing=None, location='json'),

        'description': fields.Str(required=False, missing=None, location='json'),

        'type': fields.Int(required=False, missing=VoucherType.regular_coupon.value,
                           location='json', validate=validate.OneOf(
                [l.value for l in list(VoucherType)], [l.name for l in list(VoucherType)])),

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

                        'products': fields.Nested(
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
                                    ), required=False, missing=list()
                                ),
                                'state': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ), required=False, missing=list()
                                ),
                                'city': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ), required=False, missing=list()
                                ),
                                'area': fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=0)
                                    ), required=False, missing=list()
                                ),
                                'zone': fields.List(
                                    fields.Int(), required=False, missing=list()
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

                    'benefits': fields.Nested(
                        {
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
                        },
                        required=False,
                        missing={
                            'freebies': [[]],
                            'amount': None,
                            'percentage': None,
                            'max_discount': None
                        }
                    )
                }
            ),
            missing=list(),
            location='json'
        )

    }
    args = parser.parse(coupon_create_args, request)

    # api specific validation
    success, error = validate_for_create_api_v1(args)
    if not success:
        return create_error_response(400, error)

    # general validations
    success, error = validate_for_create_coupon(args)

    if not success:
        return create_error_response(400, error)

    if args.get('type') is VoucherType.regular_coupon.value:
        rule_id_list, rule_list = create_and_save_rule_list(args)
        assert(len(rule_list) == len(rule_id_list))
        if not rule_id_list:
            return create_error_response(400, u'Unknown Exception')

        if is_timezone_aware(args.get('from')):
            args['from'] = args.get('from').replace(tzinfo=None)

        if is_timezone_aware(args.get('to')):
            args['to'] = args.get('to').replace(tzinfo=None)

        success, error = validate_for_create_voucher(args)
        if not success:
            return create_error_response(400, error)

        success_list, error_list = save_vouchers(args, rule_id_list)

        return create_success_response(success_list, error_list)
    else:
        success, data, error = create_freebie_coupon(args)
        if not success:
            return create_error_response(400, error)
        return create_success_response(data, error)


@voucher_api.route('/confirm', methods=['POST'])
@jsonify
@check_login
def confirm_order():
    confirm_order_args = {
        'order_id': fields.Str(required=True, location='json'),
        'payment_status': fields.Bool(required=True, location='json')
    }
    args = parser.parse(confirm_order_args, request)
    success, error = VoucherTransactionLog.make_transaction_log_entry(args)
    if not success:
        rv = create_error_response(400, error)
    else:
        rv = {'success': success}
    return rv


@voucher_api.route('/update/<coupon_code>', methods=['PUT', 'POST'])
@jsonify
@check_login
def update_coupon(coupon_code):
    update_coupon_args = {
        'to': fields.DateTime(required=True, location='json'),
    }
    args = parser.parse(update_coupon_args, request)

    if is_timezone_aware(args.get('to')):
        args['to'] = args.get('to').replace(tzinfo=None)

    voucher = Vouchers.find_one(coupon_code)
    if not voucher:
        return create_error_response(400, u'Voucher with code {} not found'.format(coupon_code))
    voucher.to_date = args['to']
    success = voucher.update_to_date()
    if not success:
        rv = create_error_response(400, u'Unknown Error')
    else:
        rv = {'success': success}
    return rv
