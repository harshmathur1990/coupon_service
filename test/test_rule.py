import binascii
import copy
import datetime
import json
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
        db.delete_row("auto_freebie_search")
        db.delete_row("voucher_use_tracker")
        db.delete_row("user_voucher_transaction_log")
        db.delete_row("all_vouchers")
        db.delete_row("vouchers")
        db.delete_row("rule")
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
                        "products": [2, 3],
                        "categories": {
                            "in": [1, 2],
                            "not_in": [3, 4]
                        },
                        "storefronts": [5, 6],
                        "variants": [8, 9],
                        "sellers": [45, 76],
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
                    "benefits": {
                        "amount": 100,
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(not data.get('data',dict()).get('error_list') and
                        len(data.get('data', dict()).get('success_list', list())) is 2, response.data)
        test1code1_voucher = Vouchers.find_one('TEST1CODE1')
        voucher_rule_list = test1code1_voucher.get_rule()
        rule_list = create_rule_list(rule_create_data)
        for test_rule, created_rule in zip(voucher_rule_list, rule_list):
            self.assertTrue(
                test_rule == created_rule, u'Rule passed is not equal to rule created {} - {}'.format(
                    rule_create_data, test_rule.__dict__))

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
                        "categories": {
                            "in": [1, 2],
                            "not_in": []
                        },
                        "location": {
                            "zone": [34, 56]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": {
                        "freebies": [[1, 2]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
                        "categories": {
                            "in": [1],
                            "not_in": []
                        },
                        "location": {
                            "zone": [34]
                        },
                        "valid_on_order_no": ["1+"]
                    },
                    "benefits": {
                        "freebies": [[1]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
                    "benefits": {
                        "freebies": [[1, 2, 3]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
                    "benefits": {
                        "freebies": [[1, 2, 3, 4]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
            "code": ["TEST1CODE3"],
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
                    "benefits": {
                        "freebies": [[1, 2, 3, 4, 5]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)

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
                    "benefits": {
                        "freebies": [[1, 2, 3, 4]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
                    "benefits": {
                        "freebies": [[1, 2, 3, 4, 5]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)
