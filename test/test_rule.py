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
                        "variants": [1, 2],
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
                        "variants": [1],
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
                    "benefits": {
                        "freebies": [[1]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
                    "benefits": {
                        "freebies": [[1]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 400, response.data)

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
                    "benefits": {
                        "freebies": [[1]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
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
        today = datetime.datetime.utcnow()
        tomorrow = today+timedelta(days=4)
        args = {
            'to': tomorrow.isoformat()
        }
        response = self.client.put(url_for('voucher_api/v1.update_coupon', coupon_code='TEST1CODE14'), data=json.dumps(args),
                                    content_type='application/json')
        data = json.loads(response.data)
        self.assertTrue(response.status_code == 200, response.data)

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
                        "percentage": 10,
                        "max_discount": 250
                    }
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
                        "percentage": 5,
                        "max_discount": 250
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

    def test_auto_freebie(self):
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
                        "variants": [11678],
                        "location": {
                            "zone": [2]
                        }
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
        order_data = {
            "area_id": 29557,
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": 1,
                    "quantity": 1
                },
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.check_coupon'), data=json.dumps(order_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}'.format(response.data))
        response_text = u'{"errors": [], "benefits": [{"couponCode": "TEST1CODE67", "items": [1], "paymentMode": [], "freebies": [[1]], "discount": 0.0, "type": 0, "channel": []}], "success": true, "paymentMode": [], "totalDiscount": 0.0, "products": [{"itemid": 1, "discount": 0.0, "quantity": 1}], "channel": [], "couponCodes": ["TEST1CODE67"]}'
        self.assertTrue(response.data == response_text, response.data)

    def test_apply_coupon(self):
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
                        "variants": [11678],
                        "location": {
                            "zone": [2]
                        }
                    },
                    "benefits": {
                        "freebies": [[1]]
                    }
                }
            ]
        }
        response = self.client.post(url_for('voucher_api/v1.create_voucher'), data=json.dumps(rule_create_data),
                                    content_type='application/json')
        order_data = {
            "area_id": 29557,
            "order_id": "32323",
            "customer_id": "1234",
            "channel": 0,
            "products": [
                {
                    "item_id": 1,
                    "quantity": 1
                },
            ],
            "coupon_codes": ["TEST1CODE67"]
        }
        response = self.client.post(url_for('voucher_api/v1.apply_coupon'), data=json.dumps(order_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}'.format(response.data))