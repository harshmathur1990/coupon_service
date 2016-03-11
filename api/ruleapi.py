from webargs import fields, validate
from src.enums import *
from . import api
from flask import request
from webargs.flaskparser import parser
from lib.decorator import jsonify
from src.rules.validate import validate_for_create_coupon, create_rule_object


@api.route('/<hex:id>', methods=['PUT'])
@api.route('/', methods=['POST'])
@jsonify
def create_coupon(id=None):
    coupon_create_args = {
        'name': fields.Str(required=False, missing=None, location='json'),

        'description': fields.Str(required=False, missing=None, location='json'),

        'use_type': fields.Int(required=True, location='json', validate=validate.OneOf(
            [l.value for l in list(UseType)], [l.name for l in list(UseType)])),

        'no_of_uses_allowed_per_user': fields.Int(required=False, missing=None,
                                                  validate=validate.Range(min=0), location='json'),

        'no_of_total_uses_allowed': fields.Int(required=False, missing=None,
                                               location='json', validate=validate.Range(min=0)),

        'range_min': fields.Int(required=False, missing=None,
                                location='json', validate=validate.Range(min=0)),

        'range_max': fields.Int(required=False, missing=None,
                                location='json', validate=validate.Range(min=0)),

        'channels': fields.List(
            fields.Int(
                validate=validate.OneOf(
                    [l.value for l in list(Channels)], [l.name for l in list(Channels)])),
            required=False,
            missing=list(),
            location='json'
        ),

        'brands': fields.List(
            fields.Int(
                validate=validate.Range(min=0)
            ),
            required=False,
            missing=list(),
            location='json'
        ),

        'products': fields.List(
            fields.Int(
                validate=validate.Range(min=0)
            ),
            required=False,
            missing=list(),
            location='json'
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
            missing={'in': [], 'not_in': []},
            location='json'
        ),

        'storefronts': fields.List(
            fields.Int(
                validate=validate.Range(min=0)
            ),
            required=False,
            missing=list(),
            location='json'
        ),

        'variants': fields.List(
            fields.Int(
                validate=validate.Range(min=0)
            ),
            required=False,
            missing=list(),
            location='json'
        ),

        'sellers': fields.List(
            fields.Int(
                validate=validate.Range(min=0)
            ),
            required=False,
            missing=list(),
            location='json'
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
                    fields.Str(),
                ),
            },
            required=False,
            missing={'country': [], 'state': [], 'city': [], 'area': [], 'zone': []},
            location='json'
        ),

        'payment_modes': fields.List(
            fields.Str(),
            missing=list(),
            required=False,
            location='json'
        ),

        'freebies': fields.List(
            fields.List(
                fields.Int(
                validate=validate.Range(min=0)
                ),
            ),
            required=False,
            missing=list(),
            location='json'
        ),

        'amount': fields.Int(
            required=False, missing=None, validate=validate.Range(min=0), location='json'
        ),

        'percentage': fields.Int(
            required=False, missing=None, validate=validate.Range(min=0, max=100), location='json'
        ),

        'max_discount': fields.Int(
            required=True, validate=validate.Range(min=0), location='json'
        ),

        'user_id': fields.Str(required=True)
    }
    args = parser.parse(coupon_create_args, request)
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
    rule = create_rule_object(args, id=id)
    success = rule.save()
    if not success:
        rv = {
            'success': success,
            'error': {
                'code': 400,
            }
        }
    else:
        rv = {
            'success': True,
            'data': {
                'rule_id': success
            }
        }
    return rv
