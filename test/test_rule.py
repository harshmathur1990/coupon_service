import unittest
from flask import url_for
import json
from __init__ import create_app
from src.rules.rule import Rule
from src.rules.validate import create_rule_object
import binascii
import datetime
from datetime import timedelta
from src.sqlalchemydb import CouponsAlchemyDB


class CreateRule(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        self.app_context.pop()

    def test_create_rule(self):
        # test for creation of rule,
        # try creating the same rule again and verify that no duplicate rule is created
        # try modifying the rules and update rule and verify the same
        # verify negative scenarios:
        # when any entity is not valid, or rules have semantic issues
        test_data = {
            "name": "test rule",
            "use_type": 3,
            "no_of_uses_allowed_per_user": 1,
            "no_of_total_uses_allowed": 100,
            "range_min": 250,
            "range_max": 1000,
            "channels": [0],
            "brands": [1,2],
            "products": [234,675],
            "categories": {
                "in": [54, 89],
                "not_in": [4,7]
            },
            "storefronts": [6,3],
            "variants": [90, 100],
            "sellers": [45, 78, 43, 100, 3, 7],
            "location": {
                "country": [1],
                "state": [0,1,2,3,4,5,6,7,8],
                "city": [87,45,23,45,1,4,5,34],
                "area": [56,34,67,23,67,34],
                "zone": ["ASDS34", "SDD245"]
            },
            "payment_modes": ["VISA", "AMEX"],
            "freebies": [[1,2,3,4]],
            "amount": None,
            "percentage": None,
            "max_discount": 100,
            "user_id": "10000",
            "valid_on_order_no": []
        }
        response = self.client.post(url_for('rule_api.create_coupon'), data=json.dumps(test_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
        data = json.loads(response.data)
        rule_id = data.get('data', dict()).get('rule_id', None)
        rule = Rule.find_one(rule_id)
        this_rule = create_rule_object(test_data)
        self.assertTrue(rule == this_rule,
                        u'Rule created is not same as rule pushed as json RulePushed : {} Rule Created: {} Benefits: {}'
                        .format(test_data, rule.criteria_json, rule.benefits_json))
        db = CouponsAlchemyDB()
        db.delete_row("rule", **{'id': binascii.a2b_hex(rule_id)})
        test_data = {
            "name": "test rule",
            "use_type": 3,
            "no_of_uses_allowed_per_user": 1,
            "no_of_total_uses_allowed": 100,
            "range_min": 250,
            "range_max": 1000,
            "channels": [0],
            "brands": [1,2],
            "products": [234,675],
            "categories": {
                "in": [54, 89],
                "not_in": [4,7]
            },
            "storefronts": [6,3],
            "variants": [90, 100],
            "sellers": [45, 78, 43, 100, 3, 7],
            "location": {
                "country": [1],
                "state": [0,1,2,3,4,5,6,7,8],
                "city": [87,45,23,45,1,4,5,34],
                "area": [56,34,67,23,67,34],
                "zone": ["ASDS34", "SDD245"]
            },
            "payment_modes": ["VISA", "AMEX"],
            "freebies": [[1,2,3,4]],
            "amount": 100,
            "percentage": None,
            "max_discount": 100,
            "user_id": "10000"
        }
        response = self.client.post(url_for('rule_api.create_coupon'), data=json.dumps(test_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, u'{}-{}'.format(response.data, response.status_code))

    def test_create_voucher(self):
        rule_create_data = {
            "name": "test rule",
            "use_type": 3,
            "no_of_uses_allowed_per_user": 1,
            "no_of_total_uses_allowed": 100,
            "range_min": 250,
            "range_max": 1000,
            "channels": [0],
            "brands": [1,2],
            "products": [234,675],
            "categories": {
                "in": [54, 89],
                "not_in": [4,7]
            },
            "storefronts": [6,3],
            "variants": [90, 100],
            "sellers": [45, 78, 43, 100, 3, 7],
            "location": {
                "country": [1],
                "state": [0,1,2,3,4,5,6,7,8],
                "city": [87,45,23,45,1,4,5,34],
                "area": [56,34,67,23,67,34],
                "zone": ["ASDS34", "SDD245"]
            },
            "payment_modes": ["VISA", "AMEX"],
            "freebies": [[1,2,3,4]],
            "amount": None,
            "percentage": None,
            "max_discount": 100,
            "user_id": "10000"
        }
        response = self.client.post(url_for('rule_api.create_coupon'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        rule_id = data.get('data', dict()).get('rule_id', None)
        yesterday = datetime.datetime.utcnow() - timedelta(days=1)
        voucher_create_data = {
            "code": ["PAY50", "PAY20"],
            "from": yesterday.isoformat(),
            "to": datetime.datetime.utcnow().isoformat(),
            "user_id": "10000"
        }
        response = self.client.post(url_for('rule_api.create_voucher',
                                            rule_id=rule_id), data=json.dumps(voucher_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, u'{}-{}'.format(response.data, response.status_code))
        data = json.loads(response.data)
        res = {
            "success": False,
            "error": {
                "code": 400,
                "error": [
                    "Backdated voucher creation is not allowed"
                ]
            }
        }
        self.assertTrue(data == res, u'Response does not match {} - {}'.format(data, res))
        tomorrow = datetime.datetime.utcnow() + timedelta(days=1)
        day_after = datetime.datetime.utcnow()+timedelta(days=2)
        voucher_create_data = {
            "code": ["PAY50", "PAY20"],
            "from": tomorrow.isoformat(),
            "to": day_after.isoformat(),
            "user_id": "10000"
        }
        response = self.client.post(url_for('rule_api.create_voucher', rule_id=rule_id),
                                    data=json.dumps(voucher_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 2, response.data)
        voucher_id_list = list()
        for voucher in data.get('data', dict()).get('success_list', list()):
            voucher_id_list.append(voucher.get('id'))
        db = CouponsAlchemyDB()
        for voucher in voucher_id_list:
            db.delete_row("vouchers", **{'id': binascii.a2b_hex(voucher)})
            db.delete_row("all_vouchers", **{'id': binascii.a2b_hex(voucher)})
        db.delete_row("rule", **{'id': binascii.a2b_hex(rule_id)})