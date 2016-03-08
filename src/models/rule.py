import uuid
import binascii
from src.enums import *


class Rule(object):

    def __init__(self, id=None, name=None, description=None, rule_type=None,
                 item_type=ItemType.not_available, use_type=UseType.not_available,
                 no_of_uses_allowed_per_user=None, no_of_total_uses_allowed=None,
                 range_min=None, range_max=None, amount_or_percentage=None,
                 max_discount_value=None, location_type=LocationType.not_available,
                 benefit_type=BenefitType.amount, payment_specific=False, active=True,
                 user_id=None, freebie_value_list=None, item_type_value_list=None,
                 location_value_list=None, payment_mode_list=None):
        # instantiate this class with a helper function
        if not id:
            id = uuid.uuid1()
            self.created_by = user_id
        self.id = id
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.name = name
        self.description = description
        self.rule_type = rule_type
        self.item_type = item_type
        self.use_type = use_type
        self.no_of_uses_allowed_per_user = no_of_uses_allowed_per_user
        self.no_of_total_uses_allowed = no_of_total_uses_allowed
        self.range_min = range_min
        self.range_max = range_max
        self.amount_or_percentage = amount_or_percentage
        self.max_discount_value = max_discount_value
        self.location_type = location_type
        self.benefit_type = benefit_type
        self.payment_specific = payment_specific
        self.active = active
        self.updated_by = user_id
        self.freebie_value_list = freebie_value_list
        self.item_type_value_list = item_type_value_list
        self.location_value_list = location_value_list
        self.payment_mode_list = payment_mode_list
        if not self.rule_type:
            self.get_rule_type()

    def get_rule_type(self):
        pass

    @staticmethod
    def create_amount_coupon(data_dict):
        pass

    @staticmethod
    def create_percentage_coupon(data_dict):
        pass

    @staticmethod
    def create_freebie_coupon(data_dict):
        pass

    def save_freebie_value_list(self):
        for freebie in self.freebie_value_list:
            self.save_freebie(freebie)

    def save_freebie(self, freebie):
        pass

    def save_item_value_list(self):
        for item in self.item_type_value_list:
            self.save_item(item)

    def save_item(self, item):
        pass

    def save_payment_mode_list(self):
        for payment_mode in self.payment_mode_list:
            self.save_payment_mode(payment_mode)

    def save_payment_mode(self, payment_mode):
        pass

    def save_location_value_list(self):
        for location in self.location_value_list:
            self.save_location(location)

    def save_location(self, location):
        pass

class FreebieValueList(object):
    def __init__(self, rule_id, entity_type, entity_id, user_id):
        self.rule_id = rule_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.updated_by = user_id


class ItemTypeValueList(object):
    def __init__(self, rule_id, item_id, user_id):
        self.rule_id = rule_id
        self.item_id = item_id
        self.updated_by = user_id


class LocationValueList(object):
    def __init__(self, rule_id, location_id, user_id):
        self.rule_id = rule_id
        self.location_id = location_id
        self.updated_by = user_id


class PaymentModeList(object):
    def __init__(self, rule_id, payment_mode, user_id):
        self.rule_id = rule_id
        self.payment_mode = payment_mode
        self.updated_by = user_id
