import unittest
from flask import url_for
import json
from __init__ import create_app
from src.rules.rule import Rule
from src.rules.validate import create_rule_object


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
            "range_min": None,
            "range_max": None,
            "channels": [],
            "brands": [],
            "products": [],
            "categories": {
                "in": [],
                "not_in": []
            },
            "storefronts": [],
            "variants": [],
            "sellers": [],
            "location": {
                "country": [],
                "state": [],
                "city": [],
                "area": [],
                "zone": []
            },
            "payment_modes": [],
            "amount": 100,
            "percentage": None,
            "max_discount": 100,
            "user_id": "10000"
        }
        response = self.client.post(url_for('api.create_coupon'), data=json.dumps(test_data),
                                    content_type='application/json')
        self.assertTrue(response.status_code == 200, u'{}-{}'.format(response.data, response.status_code))
        data = json.loads(response.data)
        rule_id = data.get('data', dict()).get('rule_id', None)
        rule = Rule.find_one(rule_id)
        this_rule = create_rule_object(test_data, id=rule_id)
        self.assertTrue(rule == this_rule)
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
            "amount": 100,
            "percentage": None,
            "max_discount": 100,
            "user_id": "10000"
        }
