import json
import logging
import werkzeug
from flask import request
from lib import KAFTATESTINGKEY, cache
from lib.decorator import jsonify, check_login, push_to_kafka_for_testing
from lib.utils import length_validator, create_error_response, is_old_benefit_dict_valid,\
    create_success_response, is_valid_schedule_object, is_valid_duration_string, handle_unprocessable_entity
from src.enums import VoucherType, Channels, SchedulerType
from src.rules.utils import apply_benefits, update_keys_in_input_list,\
    fetch_order_response, make_transaction_log_entry
from utils import fetch_auto_benefits, fetch_order_detail, create_regular_coupon, fetch_coupon
from src.rules.validate import validate_coupon
from src.enums import Permission
from webargs import fields, validate
from webargs.flaskparser import parser
from api import voucher_api, voucher_api_v_1_1
from validate import validate_for_create_api_v1, validate_for_update
from utils import create_freebie_coupon, create_failed_api_response, refactor_benefits
from lib.kafka_lib import CouponsKafkaProducer

logger = logging.getLogger(__name__)


@voucher_api.route('/create', methods=['POST'])
@jsonify
@push_to_kafka_for_testing
@check_login(Permission.create_voucher)
def create_voucher():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    coupon_create_args = {
        'force': fields.Bool(location='query', missing=False),

        'name': fields.Str(required=False, missing=None, location='json'),

        'description': fields.Str(required=False, missing=None, location='json'),

        'custom': fields.Str(required=False, missing=None, location='json', validate=lambda val: length_validator(val, 1000, type='string')),

        'type': fields.Int(required=False, missing=VoucherType.regular_coupon.value,
                           location='json', validate=validate.OneOf(
                [l.value for l in list(VoucherType)], [l.name for l in list(VoucherType)])),

        'user_id': fields.Str(required=False),

        'code': fields.List(fields.Str(validate=lambda val: length_validator(val, 200, type='string')), required=True, location='json'),

        'from': fields.DateTime(required=True, location='json'),

        'to': fields.DateTime(required=True, location='json'),

        'schedule': fields.List(
            fields.Nested(
                {
                    'type': fields.Int(required=True,
                                       validate=validate.OneOf(
                        [l.value for l in list(SchedulerType)], [l.name for l in list(SchedulerType)])),
                    'value': fields.Str(required=True),
                    'duration': fields.Str(required=True, validate=is_valid_duration_string)
                }
            ),
            required=False,
            missing=list(),
            validate=lambda val: length_validator(val, 250)
        ),

        'rules': fields.List(
            fields.Nested(
                {
                    'description': fields.Str(required=False),

                    'criteria': fields.Nested(
                        {
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

                            'source': fields.List(
                                fields.Str(),
                                required=False,
                                missing=list(),
                                location='json'
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
                        },
                        validate=lambda val: length_validator(val, 2000)
                    ),

                    'blacklist_criteria': fields.Nested(
                        {

                            'channels': fields.List(
                                fields.Int(
                                    validate=validate.OneOf(
                                        [l.value for l in list(Channels)], [l.name for l in list(Channels)])),
                                required=False,
                                missing=list()
                            ),

                            'source': fields.List(
                                fields.Str(),
                                required=False,
                                missing=list(),
                                location='json'
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
                        },
                        validate=lambda val: length_validator(val, 2000),
                        required=False,
                        missing=dict()
                    ),

                    'benefits': fields.Nested(
                        {
                            'freebies': fields.List(
                                fields.List(
                                    fields.Int(
                                        validate=validate.Range(min=1)
                                    ),
                                ),
                                required=False,
                                missing=list()
                            ),

                            'amount': fields.Int(
                                required=False, missing=None, validate=validate.Range(min=0)
                            ),

                            'percentage': fields.Float(
                                required=False, missing=None, validate=validate.Range(min=0, max=100)
                            ),

                            'max_discount': fields.Int(
                                required=False, validate=validate.Range(min=0)
                            ),

                            'cashback': fields.Float(
                                required=False, missing=None, validate=validate.Range(min=0)
                            ),

                            'cashback_percentage': fields.Float(
                                required=False, missing=None, validate=validate.Range(min=0)
                            )
                        },
                        required=False,
                        validate=[lambda val: length_validator(val, 1000)]
                    )
                }
            ),
            missing=list(),
            location='json'
        )

    }
    try:
        args = parser.parse(coupon_create_args, req=request, validate=is_valid_schedule_object)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    # api specific validation
    success, error = validate_for_create_api_v1(args)
    if not success:
        return create_error_response(400, error)

    # # general validations
    # success, error = validate_for_create_coupon(args)
    #
    # if not success:
    #     return create_error_response(400, error)

    if args.get('type') is VoucherType.regular_coupon.value:
        return create_regular_coupon(args)
    else:
        success, data, error = create_freebie_coupon(args)
        if not success:
            return create_error_response(400, error)
        return create_success_response(data, error)


@voucher_api.route('/confirm', methods=['POST'])
@jsonify
@push_to_kafka_for_testing
@check_login(Permission.update_order_status)
def confirm_order():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    confirm_order_args = {
        'order_id': fields.Str(required=True, location='json'),
        'payment_status': fields.Bool(required=True, location='json')
    }
    try:
        args = parser.parse(confirm_order_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    return make_transaction_log_entry(args)


@voucher_api.route('/update', methods=['PUT', 'POST'])
@jsonify
@push_to_kafka_for_testing
@check_login(Permission.update_voucher)
def update_coupon():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))

    args = request.args.to_dict()
    if args.get('force'):
        args['force'] = json.loads(args.get('force'))

    try:
        data_list = json.loads(request.get_data())
    except Exception as e:
        rv = {
            'success': False,
            'error': {
                'code': 422,
                'error': u'Unable to parse Json'
            },
            'errors': [u'Unable to parse Json']
        }
        return rv

    success, error = validate_for_update(data_list, args.get('force', False))
    if not success:
        return create_error_response(400, error)

    success_list, error_list = update_keys_in_input_list(data_list)
    return {
        'success': True,
        'data': {
            'success_list': success_list,
            'error_list': error_list
        }
    }


@voucher_api.route('/fetchDetail', methods=['POST'])
@jsonify
@push_to_kafka_for_testing
@check_login(Permission.fetch_voucher)
def get_coupon():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    get_coupon_args = {
        'coupon_codes': fields.List(fields.Str(), required=True, location='json')
    }
    try:
        args = parser.parse(get_coupon_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    return fetch_coupon(args)


@voucher_api_v_1_1.route('/apply', methods=['POST'])
@jsonify
@push_to_kafka_for_testing
@check_login(Permission.apply_voucher)
def apply_coupon_v2():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    apply_coupon_args = {
        'order_id': fields.Str(required=True, location='json'),

        'customer_id': fields.Str(required=True, location='json'),

        'area_id': fields.Str(required=True, location='json'),

        'products': fields.List(
            fields.Nested(
                {
                    'subscription_id': fields.Str(validate=validate.Length(min=1), required=False),
                    'item_id': fields.Str(validate=validate.Length(min=1), required=True),
                    'quantity': fields.Int(validate=validate.Range(min=1), required=True),
                    'coupon_codes': fields.List(
                        fields.Str(),
                        required=False
                    )
                }
            ),
            required=True,
            validate=validate.Length(min=1),
            location='json'
        ),

        'coupon_codes': fields.List(
            fields.Str(required=True, validate=validate.Length(min=1)),
            location='json',
            required=True
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

        'source': fields.Str(required=False, missing=None, location='json'),

        'payment_mode': fields.Str(required=False, missing=None, location='json'),

        'check_payment_mode': fields.Bool(location='query', missing=False)
    }
    try:
        args = parser.parse(apply_coupon_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    for product in args.get('products'):
        product['subscription_id'] = product['item_id']

    order_exists, benefits_given = fetch_order_response(args)
    if order_exists:
        return benefits_given

    success, order, error_list = fetch_order_detail(args)

    if not success:
        products = list()
        for product in args.get('products'):
            product_dict = dict()
            product_dict['itemid'] = product.get('item_id')
            product_dict['quantity'] = product.get('quantity')
            product_dict['discount'] = 0.0
            products.append(product_dict)
        rv = {
            'success': False,
            'error': {
                'code': 503,
                'error': ','.join(error_list)
            },
            'products': products,
            'freebies': [],
            'totalDiscount': 0.0,
            'channel': [],
            'paymentModes': [],
            'errors': error_list
        }
        return rv

    success, error_list = validate_coupon(args.get('coupon_codes', list()), order, validate_for_apply=True)

    if order.failed_vouchers:
        voucher_success = False
    else:
        voucher_success = True
    # coupon is valid, try applying it
    benefits = refactor_benefits(order)
    benefits['success'] = voucher_success
    benefits['errors'] = error_list
    if not voucher_success:
        benefits['error'] = {
            'code': 400,
            'error': ','.join(error_list)
        }
    else:
        benefits_applied, http_code, error = apply_benefits(args, order, benefits)
        if not benefits_applied:
            # hopefully it will never happen,
            # if it happens then only I will know what went wrong
            benefits['error'] = {
                'code': http_code,
                'error': error
            }
            benefits['errors'] = [error]
            benefits['success'] = False
    return benefits


@voucher_api_v_1_1.route('/check', methods=['POST'])
@jsonify
@push_to_kafka_for_testing
@check_login(Permission.check_voucher)
def check_coupon_v2():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    check_coupon_args = {
        'order_id': fields.Str(required=False, location='json'),

        'customer_id': fields.Str(required=True, location='json'),

        'area_id': fields.Str(required=True, location='json'),

        'products': fields.List(
            fields.Nested(
                {
                    'subscription_id': fields.Str(validate=validate.Length(min=1), required=False),
                    'item_id': fields.Str(validate=validate.Length(min=1), required=True),
                    'quantity': fields.Int(validate=validate.Range(min=1), required=True),
                    'coupon_codes': fields.List(
                        fields.Str(),
                        required=False
                    )
                }
            ),
            required=True,
            validate=validate.Length(min=1),
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

        'source': fields.Str(required=False, missing=None, location='json'),

        'payment_mode': fields.Str(required=False, missing=None, location='json'),

        'check_payment_mode': fields.Bool(location='query', missing=False)

    }
    try:
        args = parser.parse(check_coupon_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    for product in args.get('products'):
        product['subscription_id'] = product['item_id']

    success, order, error_list = fetch_order_detail(args)

    if not success:
        return create_failed_api_response(args, error_list)

    success, error_list = validate_coupon(args.get('coupon_codes', list()), order)
    if not success:
        return create_failed_api_response(args, error_list)

    if order.failed_vouchers:
        voucher_success = False
    else:
        voucher_success = True

    fetch_auto_benefits(order, VoucherType.regular_freebie)
    fetch_auto_benefits(order, VoucherType.auto_freebie)
    benefits = refactor_benefits(order)
    benefits['success'] = voucher_success
    benefits['errors'] = error_list
    if not voucher_success:
        benefits['error'] = {
            'code': 400,
            'error': ','.join(error_list)
        }
    return benefits


@voucher_api.route('/start_testing', methods=['POST'])
@jsonify
@check_login(Permission.test)
def start_testing():
    start_testing_args = {
        'test': fields.Bool(location='json', required=True),
        'seconds': fields.Int(location='json', required=False, missing=3600)
    }
    try:
        args = parser.parse(start_testing_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    cache.set(KAFTATESTINGKEY, args['test'], ex=args['seconds'])

    if not args['test']:
        CouponsKafkaProducer.destroy_instance()
    else:
        CouponsKafkaProducer.create_kafka_producer()

    rv = {
        'success': True
    }
    return rv
