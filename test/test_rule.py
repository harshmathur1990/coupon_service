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
            "type": 0,
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

    #
    # def test_check_coupon(self):
    #     tomorrow = datetime.datetime.utcnow()
    #     day_after = datetime.datetime.utcnow()+timedelta(days=2)
    #     voucher_create_data = {
    #         "name": "test rule",
    #         "use_type": 3,
    #         "no_of_uses_allowed_per_user": 1,
    #         "no_of_total_uses_allowed": 100,
    #         "range_min": 250,
    #         "range_max": 2000,
    #         "channels": [0],
    #         "brands": [131, 131, 500, 225],
    #         "products": [7645, 7538, 8772],
    #         "categories": {
    #             "in": [622, 745, 678],
    #             "not_in": [4,7]
    #         },
    #         "sellers": [9],
    #         "location": {
    #             "country": [1],
    #             "state": [47],
    #             "city": [50616],
    #             "area": [22324, 22323],
    #             "zone": [159]
    #         },
    #         "payment_modes": ["VISA", "AMEX"],
    #         "amount": None,
    #         "percentage": 10,
    #         "user_id": "10000",
    #         "code": ["PAY50", "PAY20"],
    #         "from": tomorrow.isoformat(),
    #         "to": day_after.isoformat(),
    #     }
    #     response = self.client.post(url_for('voucher_api.create_voucher'), data=json.dumps(voucher_create_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     data = json.loads(response.data)
    #     check_coupon_data = {
    #         "customer_id": "1",
    #         "area_id": 22323,
    #         "products": [
    #             {
    #                 "item_id": 2,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 3,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 4,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 5,
    #                 "quantity": 2
    #             },
    #         ],
    #         "coupon_codes": ["PAY50"],
    #         "channel": [0]
    #     }
    #     response = self.client.post(url_for('voucher_api.check_coupon'), data=json.dumps(check_coupon_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     voucher_id_list = list()
    #     for voucher in data.get('data', dict()).get('success_list', list()):
    #         voucher_id_list.append(voucher.get('id'))
    #
    #
    # def test_use_coupon(self):
    #     tomorrow = datetime.datetime.utcnow()
    #     day_after = datetime.datetime.utcnow()+timedelta(days=2)
    #     voucher_create_data = {
    #         "name": "test rule",
    #         "use_type": 3,
    #         "no_of_uses_allowed_per_user": 1,
    #         "no_of_total_uses_allowed": 100,
    #         "range_min": 250,
    #         "range_max": 2000,
    #         "channels": [0],
    #         "brands": [131, 131, 500, 225],
    #         "products": [7645, 7538, 8772],
    #         "categories": {
    #             "in": [622, 745, 678],
    #             "not_in": [4,7]
    #         },
    #         "sellers": [9],
    #         "location": {
    #             "country": [1],
    #             "state": [47],
    #             "city": [50616],
    #             "area": [22324, 22323],
    #             "zone": [159]
    #         },
    #         "payment_modes": ["VISA", "AMEX"],
    #         "amount": None,
    #         "percentage": 10,
    #         "user_id": "10000",
    #         "code": ["PAY50", "PAY20"],
    #         "from": tomorrow.isoformat(),
    #         "to": day_after.isoformat(),
    #     }
    #     response = self.client.post(url_for('voucher_api.create_voucher'), data=json.dumps(voucher_create_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     data = json.loads(response.data)
    #     use_coupon_data = {
    #         "order_id": "wjehw83728",
    #         "customer_id": "1",
    #         "area_id": 22323,
    #         "products": [
    #             {
    #                 "item_id": 2,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 3,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 4,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 5,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 7,
    #                 "quantity": 2
    #             },
    #         ],
    #         "coupon_codes": ["PAY50"],
    #         "channel": [0]
    #     }
    #     response = self.client.post(url_for('voucher_api.apply_coupon'), data=json.dumps(use_coupon_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     voucher_id_list = list()
    #     for voucher in data.get('data', dict()).get('success_list', list()):
    #         voucher_id_list.append(voucher.get('id'))
    #     db = CouponsAlchemyDB()
    #     db.delete_row("voucher_use_tracker")
    #     db.delete_row("user_voucher_transaction_log")
    #     db.delete_row("all_vouchers")
    #     db.delete_row("vouchers")
    #     db.delete_row("rule")
    #
    # def test_order_confirm(self):
    #     tomorrow = datetime.datetime.utcnow()
    #     day_after = datetime.datetime.utcnow()+timedelta(days=2)
    #     voucher_create_data = {
    #         "name": "test rule",
    #         "use_type": 3,
    #         "no_of_uses_allowed_per_user": 1,
    #         "no_of_total_uses_allowed": 100,
    #         "range_min": 250,
    #         "range_max": 2000,
    #         "channels": [0],
    #         "brands": [131, 131, 500, 225],
    #         "products": [7645, 7538, 8772],
    #         "categories": {
    #             "in": [622, 745, 678],
    #             "not_in": [4,7]
    #         },
    #         "sellers": [9],
    #         "location": {
    #             "country": [1],
    #             "state": [47],
    #             "city": [50616],
    #             "area": [22324, 22323],
    #             "zone": [159]
    #         },
    #         "payment_modes": ["VISA", "AMEX"],
    #         "amount": None,
    #         "percentage": 10,
    #         "user_id": "10000",
    #         "code": ["PAY50", "PAY20"],
    #         "from": tomorrow.isoformat(),
    #         "to": day_after.isoformat(),
    #     }
    #     response = self.client.post(url_for('voucher_api.create_voucher'), data=json.dumps(voucher_create_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     data = json.loads(response.data)
    #     use_coupon_data = {
    #         "order_id": "wjehw83728",
    #         "customer_id": "1",
    #         "area_id": 22323,
    #         "products": [
    #             {
    #                 "item_id": 2,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 3,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 4,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 5,
    #                 "quantity": 2
    #             },
    #         ],
    #         "coupon_codes": ["PAY50"],
    #         "channel": [0]
    #     }
    #     response = self.client.post(url_for('voucher_api.apply_coupon'), data=json.dumps(use_coupon_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     coupon_confirm_order_args = {
    #         'order_id': 'wjehw83728',
    #         'payment_status': True
    #     }
    #     response = self.client.post(url_for('voucher_api.confirm_order'), data=json.dumps(coupon_confirm_order_args),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     voucher_id_list = list()
    #     for voucher in data.get('data', dict()).get('success_list', list()):
    #         voucher_id_list.append(voucher.get('id'))
    #     db = CouponsAlchemyDB()
    #     db.delete_row("voucher_use_tracker")
    #     db.delete_row("user_voucher_transaction_log")
    #     db.delete_row("all_vouchers")
    #     db.delete_row("vouchers")
    #     db.delete_row("rule")
    #
    # def test_order_fail(self):
    #     tomorrow = datetime.datetime.utcnow()
    #     day_after = datetime.datetime.utcnow()+timedelta(days=2)
    #     voucher_create_data = {
    #         "name": "test rule",
    #         "use_type": 3,
    #         "no_of_uses_allowed_per_user": 1,
    #         "no_of_total_uses_allowed": 100,
    #         "range_min": 250,
    #         "range_max": 2000,
    #         "channels": [0],
    #         "brands": [131, 131, 500, 225],
    #         "products": [7645, 7538, 8772],
    #         "categories": {
    #             "in": [622, 745, 678],
    #             "not_in": [4,7]
    #         },
    #         "sellers": [9],
    #         "location": {
    #             "country": [1],
    #             "state": [47],
    #             "city": [50616],
    #             "area": [22324, 22323],
    #             "zone": [159]
    #         },
    #         "payment_modes": ["VISA", "AMEX"],
    #         "amount": None,
    #         "percentage": 10,
    #         "user_id": "10000",
    #         "code": ["PAY50", "PAY20"],
    #         "from": tomorrow.isoformat(),
    #         "to": day_after.isoformat(),
    #     }
    #     response = self.client.post(url_for('voucher_api.create_voucher'), data=json.dumps(voucher_create_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     data = json.loads(response.data)
    #     use_coupon_data = {
    #         "order_id": "wjehw83728",
    #         "customer_id": "1",
    #         "area_id": 22323,
    #         "products": [
    #             {
    #                 "item_id": 2,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 3,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 4,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 5,
    #                 "quantity": 2
    #             },
    #         ],
    #         "coupon_codes": ["PAY50"],
    #         "channel": [0]
    #     }
    #     response = self.client.post(url_for('voucher_api.apply_coupon'), data=json.dumps(use_coupon_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     coupon_confirm_order_args = {
    #         'order_id': 'wjehw83728',
    #         'payment_status': False
    #     }
    #     response = self.client.post(url_for('voucher_api.confirm_order'), data=json.dumps(coupon_confirm_order_args),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     voucher_id_list = list()
    #     for voucher in data.get('data', dict()).get('success_list', list()):
    #         voucher_id_list.append(voucher.get('id'))
    #     db = CouponsAlchemyDB()
    #     db.delete_row("voucher_use_tracker")
    #     db.delete_row("user_voucher_transaction_log")
    #     db.delete_row("vouchers")
    #     db.delete_row("all_vouchers")
    #     db.delete_row("rule")
    #
    # def test_multi_check_coupon(self):
    #     tomorrow = datetime.datetime.utcnow()
    #     day_after = datetime.datetime.utcnow()+timedelta(days=2)
    #     voucher_create_data = {
    #         "name": "test rule",
    #         "use_type": 3,
    #         "no_of_uses_allowed_per_user": 1,
    #         "no_of_total_uses_allowed": 100,
    #         "rule_type": 1,
    #         "range_min": 250,
    #         "range_max": 2000,
    #         "channels": [0],
    #         "brands": [131, 131, 500, 225],
    #         "products": [7645, 7538, 8772],
    #         "categories": {
    #             "in": [622, 745, 678],
    #             "not_in": [4,7]
    #         },
    #         "sellers": [9],
    #         "location": {
    #             "country": [1],
    #             "state": [47],
    #             "city": [50616],
    #             "area": [22324, 22323],
    #             "zone": [159]
    #         },
    #         "payment_modes": ["VISA", "AMEX"],
    #         "amount": None,
    #         "percentage": None,
    #         "freebies": [[1,2,3,4]],
    #         "user_id": "10000",
    #         "code": ["AUTOPAY"],
    #         "from": tomorrow.isoformat(),
    #         "to": day_after.isoformat(),
    #     }
    #     response = self.client.post(url_for('voucher_api.create_voucher'), data=json.dumps(voucher_create_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     data = json.loads(response.data)
    #     self.assertTrue(not data.get('data',dict()).get('error_list') and
    #                     len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
    #     voucher_create_data = {
    #         "name": "test rule",
    #         "use_type": 3,
    #         "no_of_uses_allowed_per_user": 1,
    #         "no_of_total_uses_allowed": 100,
    #         "range_min": 250,
    #         "range_max": 2000,
    #         "channels": [0],
    #         "brands": [131, 131, 500, 225],
    #         "products": [7645, 7538, 8772],
    #         "categories": {
    #             "in": [622, 745, 678],
    #             "not_in": [4,7]
    #         },
    #         "sellers": [9],
    #         "location": {
    #             "country": [1],
    #             "state": [47],
    #             "city": [50616],
    #             "area": [22324, 22323],
    #             "zone": [159]
    #         },
    #         "payment_modes": ["VISA", "AMEX"],
    #         "amount": None,
    #         "percentage": 20,
    #         "user_id": "10000",
    #         "code": ["PAY20"],
    #         "from": tomorrow.isoformat(),
    #         "to": day_after.isoformat(),
    #     }
    #     response = self.client.post(url_for('voucher_api.create_voucher'), data=json.dumps(voucher_create_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     data = json.loads(response.data)
    #     self.assertTrue(not data.get('data',dict()).get('error_list') and
    #                     len(data.get('data', dict()).get('success_list', list())) is 1, response.data)
    #     check_coupon_data = {
    #         "customer_id": "1",
    #         "area_id": 22323,
    #         "products": [
    #             {
    #                 "item_id": 2,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 3,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 4,
    #                 "quantity": 2
    #             },
    #             {
    #                 "item_id": 5,
    #                 "quantity": 2
    #             },
    #         ],
    #         "coupon_codes": ["AUTOPAY", "PAY20"],
    #         "channel": [0]
    #     }
    #     response = self.client.post(url_for('voucher_api.check_coupon'), data=json.dumps(check_coupon_data),
    #                                 content_type='application/json')
    #     self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
    #     voucher_id_list = list()
    #     for voucher in data.get('data', dict()).get('success_list', list()):
    #         voucher_id_list.append(voucher.get('id'))
    #     db = CouponsAlchemyDB()
    #     db.delete_row("voucher_use_tracker")
    #     db.delete_row("user_voucher_transaction_log")
    #     db.delete_row("all_vouchers")
    #     db.delete_row("vouchers")
    #     db.delete_row("rule")