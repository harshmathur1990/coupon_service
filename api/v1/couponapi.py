import json
import logging
import werkzeug
from flask import request
from lib.decorator import jsonify, check_login
from lib.utils import length_validator, get_utc_timezone_unaware_date_object, create_error_response,\
    create_success_response, is_valid_schedule_object, is_valid_duration_string, handle_unprocessable_entity
from src.enums import *
from src.rules.vouchers import VoucherTransactionLog, Vouchers
from src.rules.utils import apply_benefits, create_and_save_rule_list, update_keys_in_input_list,\
    save_vouchers, fetch_auto_benefits, fetch_order_response, get_benefits_new
from src.rules.validate import validate_coupon, validate_for_create_coupon,\
    validate_for_create_voucher
from webargs import fields, validate
from webargs.flaskparser import parser
from api import voucher_api, voucher_api_v_1_1
from validate import validate_for_create_api_v1, validate_for_update
from utils import create_freebie_coupon
from src.rules.rule import RuleCriteria, Benefits

logger = logging.getLogger(__name__)


@voucher_api.route('/create', methods=['POST'])
@jsonify
# @check_login
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
                        validate=lambda val: length_validator(val, 8000)
                    ),

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
                        },
                        validate=lambda val: length_validator(val, 2000)
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

    # general validations
    success, error = validate_for_create_coupon(args)

    if not success:
        return create_error_response(400, error)

    if args.get('type') is VoucherType.regular_coupon.value:
        rule_id_list, rule_list = create_and_save_rule_list(args)
        assert(len(rule_list) == len(rule_id_list))
        if not rule_id_list:
            return create_error_response(400, u'Unknown Exception')

        args['from'] = get_utc_timezone_unaware_date_object(args.get('from'))
        args['to'] = get_utc_timezone_unaware_date_object(args.get('to'))

        success, error = validate_for_create_voucher(args)
        if not success:
            return create_error_response(400, error)

        success_list, error_list = save_vouchers(args, rule_id_list)

        for s in success_list:
            del s['id']
        return create_success_response(success_list, error_list)
    else:
        success, data, error = create_freebie_coupon(args)
        if not success:
            return create_error_response(400, error)
        return create_success_response(data, error)


@voucher_api.route('/confirm', methods=['POST'])
@jsonify
# @check_login
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

    success, error = VoucherTransactionLog.make_transaction_log_entry(args)
    if not success:
        rv = create_error_response(400, error)
    else:
        rv = {'success': success}
    return rv


@voucher_api.route('/update', methods=['PUT', 'POST'])
@jsonify
# @check_login
def update_coupon():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
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

    success, error = validate_for_update(data_list)
    if not success:
        return create_error_response(400, error)

    success_list = list()
    error_list = list()
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
# @check_login
def get_coupon():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    get_coupon_args = {
        'coupon_codes': fields.List(fields.Str(), required=True, location='json')
    }
    try:
        args = parser.parse(get_coupon_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    success_list = list()
    error_list = list()
    coupon_codes = args.get('coupon_codes')
    for coupon_code in coupon_codes:
        voucher_list = Vouchers.find_all_by_code(coupon_code)
        if not voucher_list:
            error_dict = {
                'code': coupon_code,
                'error': u'Voucher code {} not found'.format(coupon_code)
            }
            error_list.append(error_dict)
            continue
        for voucher in voucher_list:
            # voucher = Vouchers.find_one(coupon_code)
            # if not voucher:
            #     error_dict = {
            #         'code': coupon_code,
            #         'error': u'Voucher code {} not found'.format(coupon_code)
            #     }
            #     error_list.append(error_dict)
            #     continue
            voucher_dict = dict()
            rules = list()
            voucher.get_rule()
            for rule in voucher.rules_list:
                criteria_obj = rule.criteria_obj
                assert isinstance(criteria_obj, RuleCriteria)
                rule_dict = dict()
                criteria = dict()
                benefits = dict()
                location_dict = dict()
                rule_dict['description'] = rule.description
                criteria['no_of_uses_allowed_per_user'] = criteria_obj.usage['no_of_uses_allowed_per_user']
                criteria['no_of_total_uses_allowed'] = criteria_obj.usage['no_of_total_uses_allowed']
                criteria['range_min'] = criteria_obj.range_min
                criteria['range_max'] = criteria_obj.range_max
                criteria['cart_range_min'] = criteria_obj.cart_range_min
                criteria['cart_range_max'] = criteria_obj.cart_range_max
                criteria['channels'] = criteria_obj.channels
                criteria['brands'] = criteria_obj.brands
                criteria['products'] = criteria_obj.products
                criteria['categories'] = criteria_obj.categories
                criteria['storefronts'] = criteria_obj.storefronts
                criteria['variants'] = criteria_obj.variants
                criteria['sellers'] = criteria_obj.sellers
                location_dict['country'] = criteria_obj.country
                location_dict['state'] = criteria_obj.state
                location_dict['city'] = criteria_obj.city
                location_dict['area'] = criteria_obj.area
                location_dict['zone'] = criteria_obj.zone
                criteria['location'] = location_dict
                criteria['valid_on_order_no'] = criteria_obj.valid_on_order_no
                criteria['payment_modes'] = criteria_obj.payment_modes
                benefits_obj = rule.benefits_obj
                assert isinstance(benefits_obj, Benefits)
                benefits['max_discount'] = benefits_obj.max_discount
                for data in benefits_obj.data:
                    type = BenefitType(data.get('type'))
                    if type is BenefitType.amount:
                        benefits['amount'] = data.get('value')
                    elif type is BenefitType.percentage:
                        benefits['percentage'] = data.get('value')
                    else:
                        benefits['freebies'] = [data.get('value')]
                if not benefits.get('freebies'):
                    benefits['freebies'] = [[]]
                rule_dict['criteria'] = criteria
                rule_dict['benefits'] = benefits
                rules.append(rule_dict)
            voucher_dict['rules'] = rules
            voucher_dict['description'] = voucher.description
            voucher_dict['from'] = voucher.from_date.isoformat()
            voucher_dict['to'] = voucher.to_date.isoformat()
            voucher_dict['code'] = voucher.code
            voucher_dict['user_id'] = voucher.created_by
            voucher_dict['type'] = voucher.type
            voucher_dict['custom'] = voucher.custom
            voucher_dict['schedule'] = voucher.schedule
            success_list.append(voucher_dict)
    return create_success_response(success_list, error_list)


@voucher_api_v_1_1.route('/apply', methods=['POST'])
@jsonify
@check_login
def apply_coupon_v2():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
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

        'source': fields.Str(required=False, missing=None, location='json')
    }
    try:
        args = parser.parse(apply_coupon_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    order_exists, benefits_given = fetch_order_response(args)
    if order_exists:
        return benefits_given
    success, order, error = validate_coupon(args, validate_for_apply=True)
    if success:
        if order.failed_vouchers:
            voucher_success = False
        else:
            voucher_success = True
        # coupon is valid, try applying it
        benefits = get_benefits_new(order)
        benefits['success'] = voucher_success
        benefits['errors'] = error
        if not voucher_success:
            benefits['error'] = {
                'code': 400,
                'error': ','.join(error)
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
    products = list()
    for product in args.get('products'):
        product_dict = dict()
        product_dict['itemid'] = product.get('item_id')
        product_dict['quantity'] = product.get('quantity')
        product_dict['discount'] = 0.0
        products.append(product_dict)
    else:
        return {
            'success': False,
            'error': {
                'code': 503,
                'error': ','.join(error)
            },
            'products': products,
            'freebies': [],
            'totalDiscount': 0.0,
            'channel': [],
            'paymentModes': [],
            'errors': error
        }


@voucher_api_v_1_1.route('/check', methods=['POST'])
@jsonify
@check_login
def check_coupon_v2():
    logger.info(u'Requested url = {} , arguments = {}'.format(request.url_rule, request.get_data()))
    check_coupon_args = {
        'order_id': fields.Str(required=False, location='json'),

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

        'source': fields.Str(required=False, missing=None, location='json')

    }
    try:
        args = parser.parse(check_coupon_args, request)
    except werkzeug.exceptions.UnprocessableEntity as e:
        return handle_unprocessable_entity(e)

    success, order, error = validate_coupon(args)

    if success:
        if order.failed_vouchers:
            voucher_success = False
        else:
            voucher_success = True
        # coupon is valid, try applying it
        fetch_auto_benefits(order, VoucherType.regular_freebie)
        fetch_auto_benefits(order, VoucherType.auto_freebie)
        benefits = get_benefits_new(order)
        benefits['success'] = voucher_success
        benefits['errors'] = error
        if not voucher_success:
            benefits['error'] = {
                'code': 400,
                'error': ','.join(error)
            }
        return benefits
    products = list()
    for product in args.get('products'):
        product_dict = dict()
        product_dict['itemid'] = product.get('item_id')
        product_dict['quantity'] = product.get('quantity')
        product_dict['discount'] = 0.0
        products.append(product_dict)
    return {
        'success': False,
        'error': {
            'code': 503,
            'error': ','.join(error)
        },
        'products': products,
        'freebies': [],
        'totalDiscount': 0.0,
        'channel': [],
        'paymentModes': [],
        'errors': error
    }
