import datetime
import json
import time
import unittest
from src.sqlalchemydb import CouponsAlchemyDB
from src.rules.utils import create_rule_list
from src.rules.vouchers import Vouchers
from datetime import timedelta
from __init__ import create_app
from flask import url_for


class CreateRule(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        db = CouponsAlchemyDB()
        db.delete_row("auto_benefits")
        db.delete_row("voucher_use_tracker")
        db.delete_row("user_voucher_transaction_log")
        db.delete_row("all_vouchers")
        db.delete_row("vouchers")
        db.delete_row("rule")
        db.delete_row("all_vouchers_log")
        self.app_context.pop()

    def test_create_voucher(self):
        # To test thar created rule is same as the rule being pushed
        # and also the vouchers are created successfully
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1", "TEST1CODE2"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "channels": [0],
                        "brands": [1, 2],
                        "products": {
                            'in':[2, 3],
                            'not_in': []
                        },
                        "categories": {
                            "in": [1, 2],
                            "not_in": [3, 4]
                        },
                        "storefronts": [5, 6],
                        "variants": [8, 9],
                        "location": {
                            "country": [1],
                            "state": [1, 4],
                            "city": [5, 8],
                            "area": [56, 90],
                            "zone": [34, 78]
                        },
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 0,
                            "amount": 100,
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 2, response.data)
        test1code1_voucher = Vouchers.find_one('TEST1CODE1')
        voucher_rule_list = test1code1_voucher.get_rule()
        from grocery.api.v1.utils import get_criteria_kwargs
        from grocery.api.v1.rule_criteria import RuleCriteria
        from src.rules.rule import Benefits
        rule_list = create_rule_list(rule_create_data, get_criteria_kwargs)
        for rule in rule_list:
            criteria_obj = rule.criteria_obj
            criteria_json = criteria_obj.canonical_json()
            benefits_obj = rule.benefits_obj
            benefits_json = benefits_obj.canonical_json()
            blacklist_criteria_obj = rule.blacklist_criteria_obj
            blacklist_criteria_json = blacklist_criteria_obj.canonical_json()
            new_criteria_dict = json.loads(criteria_json)
            new_criteria_obj = RuleCriteria(**new_criteria_dict)
            new_blacklist_criteria_dict = json.loads(blacklist_criteria_json)
            new_blacklist_criteria_obj = RuleCriteria(**new_blacklist_criteria_dict)
            new_benefits_dict = json.loads(benefits_json)
            new_benefits_obj = Benefits(**new_benefits_dict)
            rule.criteria_obj = new_criteria_obj
            rule.blacklist_criteria_obj = new_blacklist_criteria_obj
            rule.benefits_obj = new_benefits_obj
        for test_rule, created_rule in zip(voucher_rule_list, rule_list):
            self.assertTrue(
                test_rule == created_rule, u'Rule passed is not equal to rule created {} - {} - {} - {} - {} - {}'.format(
                    created_rule.criteria_obj.__dict__, test_rule.criteria_obj.__dict__, created_rule.blacklist_criteria_obj.__dict__, test_rule.blacklist_criteria_obj.__dict__, created_rule.benefits_obj.__dict__, test_rule.benefits_obj.__dict__))

    def test_create_invalid_auto_freebie(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "variants": [1, 2],
                        "location": {
                            "zone": [34, 56]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)

    def test_create_valid_auto_freebie(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "variants": [1],
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)

    def test_regular_freebie(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2, 3]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)

    def test_update_regular_freebie_fail(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE2"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2, 3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE34"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2, 3, 4, 5]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)
        self.assertTrue(data.get('error').get('error'), response.data)

    def test_update_regular_freebie_success(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE2"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2, 3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE2"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2, 3, 4, 5]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)
        self.assertTrue(data.get('error').get('error'), response.data)

    def test_auto_freebie_update_fail(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE5"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "variants": [1],
                        "location": {
                            "zone": [35]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE6"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "variants": [1],
                        "location": {
                            "zone": [35]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)
        self.assertTrue(data.get('error').get('error'), response.data)

    def test_auto_freebie_update_success(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE5"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "variants": [1],
                        "location": {
                            "zone": [35]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE5"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "variants": [1],
                        "location": {
                            "zone": [35]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)
        self.assertTrue(data.get('error').get('error'), response.data)

    def test_update_to_date_vouchers(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE14", "TEST1CODE25"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "channels": [0],
                        "brands": [1, 2, 3],
                        "products": {
                            'in':[2, 3, 4],
                            'not_in': []
                        },
                        "categories": {
                            "in": [1, 2],
                            "not_in": [3, 4]
                        },
                        "storefronts": [5, 6],
                        "variants": [8, 9],
                        "location": {
                            "country": [1],
                            "state": [1, 4],
                            "city": [5, 8],
                            "area": [56, 90],
                            "zone": [34, 78]
                        },
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 0,
                            "amount": 100,
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        today = datetime.datetime.utcnow()
        two_days_after = today+timedelta(days=2)
        four_days_after = today+timedelta(days=4)
        coupon_missing_args = [
            {
                'update': {
                    'to': two_days_after.isoformat()
                }
            },
            {
                'coupons': [{'code': 'TEST1CODE25'}],
                'update': {
                    'to': two_days_after.isoformat()
                }
            }
        ]
        response = self.client.put(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(coupon_missing_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        wrong_date_format_args = [
            {
                'coupons': [{'code': 'TEST1CODE14'}],
                'update': {
                    'to': 'dssfds'
                }
            },
            {
                'coupons': [{'code': 'TEST1CODE25'}],
                'update': {
                    'to': four_days_after.isoformat()
                }
            }
        ]
        response = self.client.put(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(wrong_date_format_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        no_date_args = [
            {
                'coupons': [{'code': 'TEST1CODE14'}],
                'update': {
                    'to': two_days_after.isoformat()
                }
            },
            {
                'coupons': [{'code': 'TEST1CODE25'}],
            }
        ]
        response = self.client.put(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(no_date_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        args = [
            {
                'coupons': [{'code': 'TEST1CODE14'}],
                'update': {
                    'to': two_days_after.isoformat()
                }
            },
            {
                'coupons': [{'code': 'TEST1CODE25'}],
                'update': {
                    'to': four_days_after.isoformat()
                }
            }
        ]
        response = self.client.put(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        partial_args = [
            {
                'coupons': [{'code': 'HARSHMATHUR'}],
                'update': {
                    'to': two_days_after.isoformat()
                }
            },
            {
                'coupons': [{'code': 'TEST1CODE25'}],
                'update': {
                    'to': four_days_after.isoformat()
                }
            }
        ]
        response = self.client.put(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(partial_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('error_list'))

    def test_multi_rule_vouchers(self):
        # To test thar created rule is same as the rule being pushed
        # and also the vouchers are created successfully
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1", "TEST1CODE2"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "channels": [0],
                        "brands": [1, 2],
                        "products": {
                            'in':[2, 3],
                            'not_in': []
                        },
                        "categories": {
                            "in": [100, 200],
                            "not_in": []
                        },
                        "storefronts": [5, 6],
                        "variants": [8, 9],
                        "location": {
                            "country": [1],
                            "state": [1, 4],
                            "city": [5, 8],
                            "area": [56, 90],
                            "zone": [34, 78]
                        },
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                },
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "channels": [0],
                        "brands": [1, 2],
                        "products": {
                            'in':[2, 3],
                            'not_in': []
                        },
                        "categories": {
                            "in": [],
                            "not_in": [100, 200]
                        },
                        "storefronts": [5, 6],
                        "variants": [8, 9],
                        "location": {
                            "country": [1],
                            "state": [1, 4],
                            "city": [5, 8],
                            "area": [56, 90],
                            "zone": [34, 78]
                        },
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 5,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 2, response.data)
        test1code1_voucher = Vouchers.find_one('TEST1CODE1')
        voucher_rule_list = test1code1_voucher.get_rule()
        from grocery.api.v1.utils import get_criteria_kwargs
        from grocery.api.v1.rule_criteria import RuleCriteria
        from src.rules.rule import Benefits
        rule_list = create_rule_list(rule_create_data, get_criteria_kwargs)
        for rule in rule_list:
            criteria_obj = rule.criteria_obj
            criteria_json = criteria_obj.canonical_json()
            benefits_obj = rule.benefits_obj
            benefits_json = benefits_obj.canonical_json()
            blacklist_criteria_obj = rule.blacklist_criteria_obj
            blacklist_criteria_json = blacklist_criteria_obj.canonical_json()
            new_criteria_dict = json.loads(criteria_json)
            new_criteria_obj = RuleCriteria(**new_criteria_dict)
            new_blacklist_criteria_dict = json.loads(blacklist_criteria_json)
            new_blacklist_criteria_obj = RuleCriteria(**new_blacklist_criteria_dict)
            new_benefits_dict = json.loads(benefits_json)
            new_benefits_obj = Benefits(**new_benefits_dict)
            rule.criteria_obj = new_criteria_obj
            rule.blacklist_criteria_obj = new_blacklist_criteria_obj
            rule.benefits_obj = new_benefits_obj
        for test_rule, created_rule in zip(voucher_rule_list, rule_list):
            self.assertTrue(
                test_rule == created_rule, u'Rule passed is not equal to rule created {} - {} - {} - {} - {} - {}'.format(
                    created_rule.criteria_obj.__dict__, test_rule.criteria_obj.__dict__, created_rule.blacklist_criteria_obj.__dict__, test_rule.blacklist_criteria_obj.__dict__, created_rule.benefits_obj.__dict__, test_rule.benefits_obj.__dict__))

    def test_check_auto_freebie(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE67"],
            "from": today.date().isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 300,
                        "range_max": 500,
                        "cart_range_min": 300,
                        "cart_range_max": 500,
                        "variants": [329327],
                        "location": {
                            "zone": [188464]
                        }
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    headers=headers, content_type='application/json')
        data = json.loads(response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    headers=headers, content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}'.format(response.data))
        data = json.loads(response.data)
        self.assertTrue(data.get('couponCodes')[0] == 'TEST1CODE67', response.data)
        self.assertTrue(data.get('benefits')[0]['freebies'] == [[1]], response.data)

    def test_apply_auto_freebie_coupon(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE67"],
            "from": today.date().isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 300,
                        "range_max": 500,
                        "cart_range_min": 300,
                        "cart_range_max": 500,
                        "variants": [329327],
                        "location": {
                            "zone": [188464]
                        }
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "order_id": "32323",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ],
            "coupon_codes": ["TEST1CODE67"]
        }

        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    headers=headers, content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}'.format(response.data))
        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    headers=headers, content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}'.format(response.data))
        data = json.loads(response.data)
        self.assertTrue(len(data.get('benefits')) == 1, response.data)

    def test_delete_and_update_auto_freebie(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        day_before = today-timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE69"],
            "from": today.date().isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 300,
                        "range_max": 500,
                        "cart_range_min": 300,
                        "cart_range_max": 500,
                        "variants": [11679],
                        "location": {
                            "zone": [3]
                        }
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)
        self.assertTrue(data.get('success'), response.data)
        db = CouponsAlchemyDB()
        all_vouchers_code_dict = db.find_one("all_vouchers", **{'code': 'TEST1CODE69'})
        expire_args = [
            {
                'coupons': [{'code': 'TEST1CODE69'}],
                'update': {
                    'to': day_before.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)
        self.assertTrue(data.get('success'), response.data)
        db = CouponsAlchemyDB()
        all_vouchers_code_dict = db.find_one("all_vouchers", **{'code': 'TEST1CODE69'})
        vouchers_code_dict = db.find_one("vouchers", **{'code': 'TEST1CODE69'})
        self.assertTrue(all_vouchers_code_dict)
        self.assertTrue(not vouchers_code_dict, vouchers_code_dict)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE69"],
            "from": datetime.datetime.utcnow().isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 300,
                        "range_max": 500,
                        "cart_range_min": 300,
                        "cart_range_max": 500,
                        "variants": [11680],
                        "location": {
                            "zone": [3]
                        }
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)
        self.assertTrue(data.get('data').get('success_list'), response.data)

    def test_overlapping_intervals_regular_freebie(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE259"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 500,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 300,
                        "cart_range_max": 700,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('error', dict()).get('error'), response.data)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 700,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('error', dict()).get('error'), response.data)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 400,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('error', dict()).get('error'), response.data)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('error', dict()).get('error'), response.data)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_max": 400,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('error', dict()).get('error'), response.data)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 501,
                        "cart_range_max": 800,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)

    def test_overlapping_intervals_regular_freebie_with_different_dates(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE259"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 500,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        day_after_tomorrow = tomorrow+timedelta(days=1)
        day_after_day_after_tomorrow = day_after_tomorrow+timedelta(days=1)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE260"],
            "from": day_after_tomorrow.isoformat(),
            "to": day_after_day_after_tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 300,
                        "cart_range_max": 700,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)
        day_after_tomorrow = day_after_day_after_tomorrow+timedelta(days=1)
        day_after_day_after_tomorrow = day_after_tomorrow+timedelta(days=1)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE261"],
            "from": day_after_tomorrow.isoformat(),
            "to": day_after_day_after_tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "cart_range_max": 700,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)
        day_after_tomorrow = day_after_day_after_tomorrow+timedelta(days=1)
        day_after_day_after_tomorrow = day_after_tomorrow+timedelta(days=1)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE262"],
            "from": day_after_tomorrow.isoformat(),
            "to": day_after_day_after_tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 400,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)
        day_after_tomorrow = day_after_day_after_tomorrow+timedelta(days=1)
        day_after_day_after_tomorrow = day_after_tomorrow+timedelta(days=1)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE263"],
            "from": day_after_tomorrow.isoformat(),
            "to": day_after_day_after_tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 100,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)
        day_after_tomorrow = day_after_day_after_tomorrow+timedelta(days=1)
        day_after_day_after_tomorrow = day_after_tomorrow+timedelta(days=1)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE264"],
            "from": day_after_tomorrow.isoformat(),
            "to": day_after_day_after_tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_max": 400,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)
        day_after_tomorrow = day_after_day_after_tomorrow+timedelta(days=1)
        day_after_day_after_tomorrow = day_after_tomorrow+timedelta(days=1)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE265"],
            "from": day_after_tomorrow.isoformat(),
            "to": day_after_day_after_tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 501,
                        "cart_range_max": 800,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[3, 4]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        data = json.loads(response.data)
        self.assertTrue(data.get('data', dict()).get('success_list'), response.data)

    def test_check_and_apply_coupon_false_partial_success_iff_all_validate(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_auto_freebie_1",
            "description": "test_auto_freebie_description_1",
            "type": 0,
            "user_id": "1000",
            "code": ["TEST1CODE67"],
            "from": today.date().isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 300,
                        "range_max": 500,
                        "cart_range_min": 300,
                        "cart_range_max": 500,
                        "variants": [329327],
                        "location": {
                            "zone": [188464]
                        }
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        "channels": [],
                        "brands": [],
                        "products": {
                            'in':[],
                            'not_in': []
                        },
                        "categories": {
                            "in": [],
                            "not_in": []
                        },
                        "storefronts": [],
                        "variants": [],
                        "sellers": [],
                        "location": {
                            "country":[],
                            "state": [],
                            "city": [],
                            "area": [],
                            "zone": []
                        },
                        "payment_modes": [],
                        "valid_on_order_no": [],
                        "source": ["affiliate", "organic"]
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
        test1code1_voucher = Vouchers.find_one('TEST1CODE1')
        voucher_rule_list = test1code1_voucher.get_rule()
        from grocery.api.v1.utils import get_criteria_kwargs
        from grocery.api.v1.rule_criteria import RuleCriteria
        from src.rules.rule import Benefits
        rule_list = create_rule_list(rule_create_data, get_criteria_kwargs)
        for rule in rule_list:
            criteria_obj = rule.criteria_obj
            criteria_json = criteria_obj.canonical_json()
            benefits_obj = rule.benefits_obj
            benefits_json = benefits_obj.canonical_json()
            blacklist_criteria_obj = rule.blacklist_criteria_obj
            blacklist_criteria_json = blacklist_criteria_obj.canonical_json()
            new_criteria_dict = json.loads(criteria_json)
            new_criteria_obj = RuleCriteria(**new_criteria_dict)
            new_blacklist_criteria_dict = json.loads(blacklist_criteria_json)
            new_blacklist_criteria_obj = RuleCriteria(**new_blacklist_criteria_dict)
            new_benefits_dict = json.loads(benefits_json)
            new_benefits_obj = Benefits(**new_benefits_dict)
            rule.criteria_obj = new_criteria_obj
            rule.blacklist_criteria_obj = new_blacklist_criteria_obj
            rule.benefits_obj = new_benefits_obj
        for test_rule, created_rule in zip(voucher_rule_list, rule_list):
            self.assertTrue(
                test_rule == created_rule, u'Rule passed is not equal to rule created {} - {} - {} - {} - {} - {}'.format(
                    created_rule.criteria_obj.__dict__, test_rule.criteria_obj.__dict__, created_rule.blacklist_criteria_obj.__dict__, test_rule.blacklist_criteria_obj.__dict__, created_rule.benefits_obj.__dict__, test_rule.benefits_obj.__dict__))

        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ],
            "coupon_codes": ["TEST1CODE1"],
            "source": "organic"
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    headers=headers, content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}'.format(response.data))
        data = json.loads(response.data)
        self.assertTrue(data.get('success'), response.data)
        self.assertTrue(len(data.get('benefits')) == 2, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ],
            "coupon_codes": ["TEST1CODE1", "INVALIDCOUPON"],
            "order_id": "1234",
            "source": "organic"
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    headers=headers, content_type='application/json')
        self.assertTrue(response.status_code == 400, u'{}'.format(response.data))
        data = json.loads(response.data)
        self.assertTrue(not data.get('success'), response.data)
        self.assertTrue(len(data.get('benefits')) == 2, response.data)
        self.assertTrue(data.get('error', dict()).get('error') == u'Oops! The coupon applied is either invalid or has expired', response.data)
        order_data = {
             "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                 {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ],
            "coupon_codes": ["TEST1CODE1", "INVALIDCOUPON", "TEST1CODE67"],
            "order_id": "1234",
            "source": "organic"
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    headers=headers, content_type='application/json')
        self.assertTrue(response.status_code == 400, u'{}'.format(response.data))
        data = json.loads(response.data)
        self.assertTrue(not data.get('success'), response.data)
        self.assertTrue(len(data.get('benefits')) == 2, response.data)
        self.assertTrue(data.get('error', dict()).get('error') == u'Oops! The coupon applied is either invalid or has expired', response.data)

    def test_update_to_date_auto_freebie_fail_because_it_overlaps_with_existing_freebie(self):
        # All the freebies created are of overlapping ranges, but at a time only one will be active
        # Create a freebie and Expire it.
        # Set the to_date to some future date.
        # Set the date as some date in the past or expire it
        # Create the freebie with some other code and same criteria
        # Then try to change to_date to future of the recent expired freebie and verify that
        # it gives an error of a freebie existing with the range clash with code
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        day_before = today-timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE259"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 500,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        expire_args = [
            {
                'coupons': [{'code': 'TEST1CODE259'}],
                'update': {
                    'to': day_before.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(not voucher_dict, response.data)
        future_args = [
            {
                'coupons': [{'code': 'TEST1CODE259'}],
                'update': {
                    'to': tomorrow.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(future_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(voucher_dict)
        expire_args = [
            {
                'coupons': [{'code': 'TEST1CODE259'}],
                'update': {
                    'to': day_before.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(not voucher_dict)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE271"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 500,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE271'})
        self.assertTrue(voucher_dict)
        future_args = [
            {
                'coupons': [{'code': 'TEST1CODE259'}],
                'update': {
                    'to': tomorrow.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(future_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(not voucher_dict)

    def test_output_for_prorated_percentage(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow().date()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        "channels": [],
                        "brands": [],
                        "products": {
                            'in':[],
                            'not_in': []
                        },
                        "categories": {
                            "in": [],
                            "not_in": []
                        },
                        "storefronts": [],
                        "variants": [],
                        "sellers": [],
                        "location": {
                            "country":[],
                            "state": [],
                            "city": [],
                            "area": [],
                            "zone": []
                        },
                        "payment_modes": [],
                        "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        data = json.loads(response.data)
        self.assertTrue(data.get('benefits')[0]['max_cap'] == 250, response.data)
        self.assertTrue(data.get('benefits')[0]['amount'] < data.get('benefits')[0]['max_cap'], response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "9831314343",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 10
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 100
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        data = json.loads(response.data)
        self.assertTrue(data.get('benefits')[0]['max_cap'] == 250, response.data)
        self.assertTrue(data.get('benefits')[0]['amount'] > data.get('benefits')[0]['max_cap'], response.data)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE78"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 0,
                            "amount": 300
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        order_data = {
            "area_id": "87000",
            "customer_id": "9831314343",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 10
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 100
                },
            ],
            "coupon_codes": ["TEST1CODE78"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        #print response.data
        data = json.loads(response.data)
        self.assertTrue(not data.get('benefits')[0]['max_cap'], response.data)
        self.assertTrue(data.get('benefits')[0]['amount'] == 300, response.data)
        order_data = {
            "order_id": "AGTEST",
            "area_id": "87000",
            "customer_id": "9831314343",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 10
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 100
                },
            ],
            "coupon_codes": ["TEST1CODE78"]
        }

        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        confirm_data = {
            "order_id": "AGTEST",
            "payment_status": True
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.confirm_order'), data=json.dumps(confirm_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        confirm_data = {
            "order_id": "AGTEST",
            "payment_status": False
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.confirm_order'), data=json.dumps(confirm_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)

    def test_scheduling(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        hour = today.hour
        hour -= 1
        today = today.date()
        tomorrow = today+timedelta(days=2)
        nowtime = datetime.datetime.utcnow()
        oldtime = timedelta(minutes=10)
        oldfromnowtime = (nowtime - oldtime).time().isoformat()
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "schedule": [
                {
                    "type": 0, # 2
                    "value": oldfromnowtime, #"17:00:00", # "0 0 "+str(hour)+" 1/1 * ? *",
                    "duration": "::2::"
                }
            ],
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        #print response.data
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 4
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'), response.data)
        self.assertTrue(len(data.get('benefits')) == 1, response.data)

    def test_custom_benefit(self):
        # deprecating the custom cashback feature in favour of benefit tyoe cashback
        pass
        # values = {
        #     'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
        #     'agent_id': 1,
        #     'agent_name': u'askmegrocery',
        #     'created_at': datetime.datetime.utcnow(),
        #     'last_accessed_at': datetime.datetime.utcnow()
        # }
        # db = CouponsAlchemyDB()
        # # db.insert_row("tokens", **values)
        # headers = {
        #     'X-API-USER': 'askmegrocery',
        #     'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        # }
        # today = datetime.datetime.utcnow()
        # hour = today.hour
        # hour -= 1
        # today = today.date()
        # tomorrow = today+timedelta(days=2)
        # rule_create_data = {
        #     "name": "test_rule_1",
        #     "description": "test_some_description_1",
        #     "type": 2,
        #     "user_id": "1000",
        #     "code": ["TEST1CODE1"],
        #     "from": today.isoformat(),
        #     "to": tomorrow.isoformat(),
        #     "custom": "ICICI CASHBACK 500",
        #     "rules": [
        #         {
        #             "description": "TEST1RULE1DESCRIPTION1",
        #             "criteria": {
        #                 "no_of_uses_allowed_per_user": 1,
        #                 "no_of_total_uses_allowed": 100,
        #                 "range_min": None,
        #                 "range_max": None,
        #                 "cart_range_min": 100,
        #                 "cart_range_max": None,
        #                 "channels": [],
        #                 "brands": [],
        #                 "products": {
        #                     'in':[],
        #                     'not_in': []
        #                 },
        #                 "categories": {
        #                     "in": [],
        #                     "not_in": []
        #                 },
        #                 "storefronts": [],
        #                 "variants": [],
        #                 "sellers": [],
        #                 "location": {
        #                     "country":[],
        #                     "state": [],
        #                     "city": [],
        #                     "area": [],
        #                     "zone": []
        #                 },
        #                 "payment_modes": [],
        #                 "valid_on_order_no": []
        #             },
        #             "benefits": [
        #                 {
        #                     'type': 0,
        #                     "amount": 0
        #                 }
        #             ]
        #         }
        #     ]
        # }
        # response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
        #                             content_type='application/json')
        # self.assertTrue(response.status_code == 200, response.data)
        # order_data = {
        #     "area_id": "87000",
        #     "customer_id": "1234",
        #     "channel": 0,
        #     "products": [
        #         {
        #             "item_id": "1151594",
        #             "quantity": 4
        #         },
        #     ],
        #     "coupon_codes": ["TEST1CODE1"]
        # }
        # response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
        #                             content_type='application/json', headers=headers)
        # data = json.loads(response.data)
        # self.assertTrue(data.get('success'), response.data)
        # self.assertTrue(len(data.get('benefits')) == 1, response.data)

    def test_update_to_date(self):
        # 1. To verify that we can successfully update an expired coupon
        #    when there is no active coupon present.
        # 2. To verify that updating a coupon fails if there exists a voucher after that in chronological order
        #    be it active or inactive
        # 3. To update to_date of a voucher which is in future and present, fail if the to_date clashes with some other, else
        #    update successfully
        # 4. To delete a voucher in future
        # 5. To fail while deleting a voucher which is already history.
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow().date()
        tomorrow = today+timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        day_after_day_after = day_after + timedelta(days=1)
        rule_1_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": day_after.isoformat(),
            "to": day_after_day_after.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher', force=True), data=json.dumps(rule_1_create_data),

                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
        voucher = Vouchers.find_one('TEST1CODE1')
        self.assertTrue(voucher.to_date == datetime.datetime.combine(day_after_day_after, datetime.datetime.min.time()))
        rule_2_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        "channels": [],
                        "brands": [],
                        "products": {
                            'in':[],
                            'not_in': []
                        },
                        "categories": {
                            "in": [],
                            "not_in": []
                        },
                        "storefronts": [],
                        "variants": [],
                        "sellers": [],
                        "location": {
                            "country":[],
                            "state": [],
                            "city": [],
                            "area": [],
                            "zone": []
                        },
                        "payment_modes": [],
                        "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher', force=True), data=json.dumps(rule_2_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
        voucher = Vouchers.find_one('TEST1CODE1')
        self.assertTrue(voucher.to_date == datetime.datetime.combine(tomorrow, datetime.datetime.min.time()))
        yesterday = today - timedelta(days=4)
        expire_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': today.isoformat()}],
                'update': {
                    'to': yesterday.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        voucher = Vouchers.find_one('TEST1CODE1')
        self.assertTrue(voucher.to_date == datetime.datetime.combine(day_after_day_after, datetime.datetime.min.time()))
        voucher_list = Vouchers.find_all_by_code('TEST1CODE1')
        self.assertTrue(len(voucher_list) == 2)
        now = datetime.datetime.utcnow()
        fifteen_minutes_later = now + timedelta(minutes=15)
        rule_2_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": now.isoformat(),
            "to": fifteen_minutes_later.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        "channels": [],
                        "brands": [],
                        "products": {
                            'in':[],
                            'not_in': []
                        },
                        "categories": {
                            "in": [],
                            "not_in": []
                        },
                        "storefronts": [],
                        "variants": [],
                        "sellers": [],
                        "location": {
                            "country":[],
                            "state": [],
                            "city": [],
                            "area": [],
                            "zone": []
                        },
                        "payment_modes": [],
                        "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher', force=True), data=json.dumps(rule_2_create_data),
                                    content_type='application/json')
        failed_update_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': today.isoformat()}],
                'update': {
                    'to': tomorrow.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(failed_update_args),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('success_list') and
                        len(data.get('data', dict()).get('error_list', list())) is 1, response.data)
        day_after_day_after_day_after = day_after_day_after + timedelta(days=1)
        day_after_day_after_day_after_day_after = day_after_day_after_day_after + timedelta(days=1)
        rule_2_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": day_after_day_after_day_after.isoformat(),
            "to": day_after_day_after_day_after_day_after.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        "channels": [],
                        "brands": [],
                        "products": {
                            'in':[],
                            'not_in': []
                        },
                        "categories": {
                            "in": [],
                            "not_in": []
                        },
                        "storefronts": [],
                        "variants": [],
                        "sellers": [],
                        "location": {
                            "country":[],
                            "state": [],
                            "city": [],
                            "area": [],
                            "zone": []
                        },
                        "payment_modes": [],
                        "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher', force=True), data=json.dumps(rule_2_create_data),
                                    content_type='application/json')
        failed_update_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': day_after.isoformat()}],
                'update': {
                    'to': day_after_day_after_day_after_day_after.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(failed_update_args),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('success_list') and
                        len(data.get('data', dict()).get('error_list', list())) is 1, response.data)
        delete_update_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': day_after_day_after_day_after.isoformat()}],
                'update': {
                    'to': yesterday.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(delete_update_args),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
        voucher_list = Vouchers.find_all_by_code('TEST1CODE1')
        self.assertTrue(len(voucher_list) == 3)

    def test_full_update_api(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow().date()
        tomorrow = today+timedelta(days=1)
        day_after = tomorrow + timedelta(days=1)
        day_after_day_after = day_after + timedelta(days=1)
        rule_1_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": day_after.isoformat(),
            "to": day_after_day_after.isoformat(),
            "custom": "Some Custom 1",
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_1_create_data),
                                    content_type='application/json')
        update_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': day_after.isoformat()}],
                'update': {
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(update_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 400, response.data)
        update_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': day_after.isoformat()}],
                'update': {
                    "custom": "Some Custom 2",
                    "description": "test_some_description_2"
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(update_args),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
        voucher = Vouchers.find_one('TEST1CODE1')
        voucher_in_all_voucher = db.find_one("all_vouchers", **{'code': 'TEST1CODE1'})
        self.assertTrue(voucher.custom == 'Some Custom 2', voucher.__dict__)
        self.assertTrue(voucher.description == 'test_some_description_2', voucher.__dict__)

    def test_blacklisting(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        hour = today.hour
        hour -= 1
        today = today.date()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "custom": "ICICI CASHBACK 500",
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "blacklist_criteria": {
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": None,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        "categories": {
                            "in": [581],
                            # "not_in": []
                        },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        data = json.loads(response.data)
        self.assertTrue(data.get('success'), response.data)
        self.assertTrue(len(data.get('benefits')) == 1, response.data)
        self.assertTrue("4" in data.get('benefits')[0]['items'] and "3" in data.get('benefits')[0]['items'] and "2" not in data.get('benefits')[0]['items'] and "1" in data.get('benefits')[0]['items'], response.data)

    def test_update_to_date_backward_compatible(self):
        # All the freebies created are of overlapping ranges, but at a time only one will be active
        # Create a freebie and Expire it.
        # Set the to_date to some future date.
        # Set the date as some date in the past or expire it
        # Create the freebie with some other code and same criteria
        # Then try to change to_date to future of the recent expired freebie and verify that
        # it gives an error of a freebie existing with the range clash with code
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        day_before = today-timedelta(days=2)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE259"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 500,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        expire_args = [
            {
                'coupons': ['TEST1CODE259'],
                'update': {
                    'to': day_before.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(not voucher_dict)
        future_args = [
            {
                'coupons': ['TEST1CODE259'],
                'update': {
                    'to': tomorrow.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(future_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(voucher_dict)
        expire_args = [
            {
                'coupons': ['TEST1CODE259'],
                'update': {
                    'to': day_before.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(not voucher_dict)
        rule_create_data = {
            "name": "test_regular_freebie_1",
            "description": "test_regular_freebie_description_1",
            "type": 1,
            "user_id": "1000",
            "code": ["TEST1CODE271"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "cart_range_min": 200,
                        "cart_range_max": 500,
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": [
                        {
                            'type': 2,
                            "freebies": [[1, 2]]
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE271'})
        self.assertTrue(voucher_dict)
        future_args = [
            {
                'coupons': ['TEST1CODE259'],
                'update': {
                    'to': tomorrow.isoformat()
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(future_args),
                                    content_type='application/json')
        db = CouponsAlchemyDB()
        voucher_dict = db.find_one("vouchers", **{'code': 'TEST1CODE259'})
        self.assertTrue(not voucher_dict)

    def test_payment_mode_in_check_and_apply(self):
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        hour = today.hour
        hour -= 1
        today = today.date()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "custom": "ICICI CASHBACK 500",
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        "payment_modes": ["VISA"],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"],
            "payment_mode": "VISA"
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        #print response.data
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"],
            "payment_mode": "VISA"
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon', check_payment_mode=True), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon', check_payment_mode=True), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 400, response.data)

    def test_apply_when_same_order_id(self):
        # 1. To check that when an order is given with same order id, it should reevaluate and update
        #    voucher_use_tracker and add entry in voucher_use_transaction_log. Also check if the user id
        #    has changed, then the same must have been updated in voucher_use_tracker.
        # 2. When a date is provided check that voucher which was valid on that particular date is picked
        #    and reevaluate the coupon and check that voucher_use_tracker is up to date.
        # 3. When validate=False is given as query parameter, see if the usage check is bypassed.
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        hour = today.hour
        hour -= 1
        today = today.date()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "custom": "ICICI CASHBACK 500",
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 1,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        # "payment_modes": [],
                        # "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "order_id": "12345",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        order_data = {
            "area_id": "87000",
            "customer_id": "4321",
            "order_id": "12345",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        use_dict = db.find("voucher_use_tracker")[0]
        self.assertTrue(use_dict['user_id'] == "4321")
        order_data = {
            "area_id": "87000",
            "customer_id": "4321",
            "order_id": "123456",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 400, response.data)
        use_dict = db.find("voucher_use_tracker")[0]
        self.assertTrue(use_dict['user_id'] == "4321")
        order_data = {
            "area_id": "87000",
            "customer_id": "4321",
            "order_id": "123456",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.apply_coupon', validate=False), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        use_dict = db.find("voucher_use_tracker")[0]
        self.assertTrue(use_dict['user_id'] == "4321")

    def test_is_active_feature(self):
        # 1. To set is_active false for vouchers using update api and verify the sanity
        # 2. To check the audit trail.
        values = {
            'token': u'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy',
            'agent_id': 1,
            'agent_name': u'askmegrocery',
            'created_at': datetime.datetime.utcnow(),
            'last_accessed_at': datetime.datetime.utcnow()
        }
        db = CouponsAlchemyDB()
        # db.insert_row("tokens", **values)
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        hour = today.hour
        hour -= 1
        today = today.date()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "custom": "ICICI CASHBACK 500",
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        # "channels": [],
                        # "brands": [],
                        # "products": {
                        #     'in':[],
                        #     'not_in': []
                        # },
                        # "categories": {
                        #     "in": [],
                        #     "not_in": []
                        # },
                        # "storefronts": [],
                        # "variants": [],
                        # "sellers": [],
                        # "location": {
                        #     "country":[],
                        #     "state": [],
                        #     "city": [],
                        #     "area": [],
                        #     "zone": []
                        # },
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher', force=True), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)

        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": "1",
                    "subscription_id": "1151594",
                    "quantity": 5
                },
                {
                    "item_id": "2",
                    "subscription_id": "2007982",
                    "quantity": 5
                },
                {
                    "item_id": "3",
                    "subscription_id": "1151596",
                    "quantity": 5
                },
                {
                    "item_id": "4",
                    "subscription_id": "1151587",
                    "quantity": 5
                },
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 200, response.data)
        expire_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': today.isoformat()}],
                'update': {
                    'is_active': False
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        db = CouponsAlchemyDB()
        voucher = Vouchers.find_one('TEST1CODE1')
        self.assertTrue(voucher is False)
        expire_args = [
            {
                'coupons': [{'code': 'TEST1CODE1', 'from': today.isoformat()}],
                'update': {
                    'is_active': True
                }
            }
        ]
        response = self.client.post(url_for('grocery_voucher_api/v1.update_coupon'), data=json.dumps(expire_args),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)
        voucher = Vouchers.find_one('TEST1CODE1')
        self.assertTrue(voucher is not False)
        db = CouponsAlchemyDB()
        query = 'select max(change_id) as id from all_vouchers_log'
        max_id = db.execute_raw_sql(query, dict())[0]['id']
        all_voucher_log = db.find_one("all_vouchers_log", **{'change_id': max_id})
        vouchers = db.find_one("all_vouchers")
        del all_voucher_log['auto_id']
        del all_voucher_log['change_id']
        del all_voucher_log['changed_on']
        self.assertTrue(vouchers == all_voucher_log, u'{} - {}'.format(vouchers, all_voucher_log))
        pass

    def test_allow_zero_amount(self):
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1", "TEST1CODE2"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": 100,
                        "range_max": 1000,
                        "cart_range_min": 100,
                        "cart_range_max": 1000,
                        "channels": [0],
                        "brands": [1, 2],
                        "products": {
                            'in':[2, 3],
                            'not_in': []
                        },
                        "categories": {
                            "in": [1, 2],
                            "not_in": [3, 4]
                        },
                        "storefronts": [5, 6],
                        "variants": [8, 9],
                        "sellers": ["45", "76"],
                        "location": {
                            "country": [1],
                            "state": [1, 4],
                            "city": [5, 8],
                            "area": [56, 90],
                            "zone": [34, 78]
                        },
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": ["1+"]
                    }
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 2, response.data)
        test1code1_voucher = Vouchers.find_one('TEST1CODE1')
        voucher_rule_list = test1code1_voucher.get_rule()
        from grocery.api.v1.utils import get_criteria_kwargs
        from grocery.api.v1.rule_criteria import RuleCriteria
        from src.rules.rule import Benefits
        rule_list = create_rule_list(rule_create_data, get_criteria_kwargs)
        for rule in rule_list:
            criteria_obj = rule.criteria_obj
            criteria_json = criteria_obj.canonical_json()
            benefits_obj = rule.benefits_obj
            benefits_json = benefits_obj.canonical_json()
            blacklist_criteria_obj = rule.blacklist_criteria_obj
            blacklist_criteria_json = blacklist_criteria_obj.canonical_json()
            new_criteria_dict = json.loads(criteria_json)
            new_criteria_obj = RuleCriteria(**new_criteria_dict)
            new_blacklist_criteria_dict = json.loads(blacklist_criteria_json)
            new_blacklist_criteria_obj = RuleCriteria(**new_blacklist_criteria_dict)
            new_benefits_dict = json.loads(benefits_json)
            new_benefits_obj = Benefits(**new_benefits_dict)
            rule.criteria_obj = new_criteria_obj
            rule.blacklist_criteria_obj = new_blacklist_criteria_obj
            rule.benefits_obj = new_benefits_obj
        for test_rule, created_rule in zip(voucher_rule_list, rule_list):
            self.assertTrue(
                test_rule == created_rule, u'Rule passed is not equal to rule created {} - {} - {} - {}'.format(
                    test_rule.criteria_obj.__dict__,  test_rule.benefits_obj.__dict__, created_rule.criteria_obj.__dict__,  created_rule.benefits_obj.__dict__))

    def test_empty_product_list(self):
        headers= {
            'X-API-USER': 'askmegrocery',
            'X-API-TOKEN': 'M2JmN2U5NGYtMDJlNi0xMWU2LWFkZGQtMjRhMDc0ZjE1MGYy'
        }
        today = datetime.datetime.utcnow()
        hour = today.hour
        hour -= 1
        today = today.date()
        tomorrow = today+timedelta(days=2)
        rule_create_data = {
            "name": "test_rule_1",
            "description": "test_some_description_1",
            "type": 2,
            "user_id": "1000",
            "code": ["TEST1CODE1"],
            "from": today.isoformat(),
            "to": tomorrow.isoformat(),
            "custom": "ICICI CASHBACK 500",
            "rules": [
                {
                    "description": "TEST1RULE1DESCRIPTION1",
                    "criteria": {
                        "no_of_uses_allowed_per_user": 1,
                        "no_of_total_uses_allowed": 100,
                        "range_min": None,
                        "range_max": None,
                        "cart_range_min": 100,
                        "cart_range_max": None,
                        "payment_modes": ["VISA"],
                        "valid_on_order_no": []
                    },
                    "benefits": [
                        {
                            'type': 1,
                            "percentage": 10,
                            "max_cap": 250
                        }
                    ]
                }
            ]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.create_voucher', force=True), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, response.data)

        order_data = {
            "area_id": "87000",
            "customer_id": "1234",
            "channel": 0,
            "products": [
            ],
            "coupon_codes": ["TEST1CODE1"]
        }
        response = self.client.post(url_for('grocery_voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json', headers=headers)
        self.assertTrue(response.status_code == 422, response.data)