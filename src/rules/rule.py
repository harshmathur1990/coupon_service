import binascii
import hashlib
import logging
import importlib
import canonicaljson
from src.enums import BenefitType, MatchStatus
from src.sqlalchemydb import CouponsAlchemyDB
from config import method_dict
import copy

logger = logging.getLogger()


class Benefits(object):
    def __init__(self, **kwargs):
        max_discount = kwargs.get('max_discount', kwargs.get('maximum_discount', None))
        self.data = kwargs.get('data')
        self.data.sort()
        for data in self.data:
            if 'max_cap' not in data \
                    and data['type'] is BenefitType.percentage.value \
                    and max_discount:
                data['max_cap'] = max_discount

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        self_dict = copy.deepcopy(self.__dict__)
        max_discount = self_dict.get('max_discount')
        if max_discount:
            for data in self_dict['data']:
                if data['type'] == 1:
                    data['max_cap'] = max_discount

        data_list = list()
        for data in self_dict['data']:
            if data['value']:
                if 'max_cap' in data and not data['max_cap']:
                    del data['max_cap']
                data_list.append(data)

        self_dict['data'] = data_list
        return canonicaljson.encode_canonical_json(self_dict)


class BenefitsData(object):
    def __init__(self, **kwargs):
        self.type = kwargs.get('type')
        self.value = kwargs.get('value')
        self.max_cap = kwargs.get('max_cap')
        if self.type == BenefitType.freebie.value:
            self.value.sort()


class Rule(object):

    def __init__(self, **kwargs):
        rule_criteria_class = getattr(
            importlib.import_module(
                method_dict.get('criteria_class')['package']),
            method_dict.get('criteria_class')['attribute'])
        # instantiate this class with a helper function
        id = kwargs.get('id')  # id should be uuid.uuid1().hex
        self.id = id
        if self.id:
            self.id_bin = binascii.a2b_hex(self.id)
        self.name = kwargs.get('name')
        self.description = kwargs.get('description')
        self.criteria_obj = kwargs.get('criteria_obj')
        self.criteria_json = kwargs.get('criteria_json')
        self.blacklist_criteria_obj = kwargs.get('blacklist_criteria_obj')
        self.blacklist_criteria_json = kwargs.get('blacklist_criteria_json')
        self.benefits_json = kwargs.get('benefits_json')
        self.benefits_obj = kwargs.get('benefits_obj')
        self.sha2hash = kwargs.get('sha2hash')
        self.active = kwargs.get('active', True)
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        if not self.criteria_obj:
            criteria_dict = canonicaljson.json.loads(self.criteria_json)
            self.criteria_obj = rule_criteria_class(**criteria_dict)
        if not self.blacklist_criteria_obj and self.blacklist_criteria_json is not None:
            blacklist_criteria_dict = canonicaljson.json.loads(self.blacklist_criteria_json)
            self.blacklist_criteria_obj = rule_criteria_class(**blacklist_criteria_dict)
        if not self.benefits_obj:
            benefits_dict = canonicaljson.json.loads(self.benefits_json)
            self.benefits_obj = Benefits(**benefits_dict)

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        # update_cache = False
        try:
            # check if the rule being created already exists, if yes, just return rule id
            existing_rule = db.find_one("rule", **{'id': self.id_bin})
            if existing_rule:
                # call is to update the existing rule with new attributes, just update and save it
                # update_cache = True
                logger.error('Trying to update an existing rule {}'.format(self.__dict__))
                assert False, "A Rule is immutable."
            # no existing rule exists for this id, now check if a rule exists for given attributes
            rule_list = db.find("rule", **{'sha2hash': values.get('sha2hash')})
            if rule_list:
                for rule in rule_list:
                    rule['id'] = binascii.b2a_hex(rule['id'])
                    rule_obj = Rule(**rule)
                    if self == rule_obj:
                        self.id = rule_obj.id
                        break
            else:
                # update_cache = True
                db.insert_row("rule", **values)
            db.commit()
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False
        # else:
        #     db.commit()
        # if update_cache:
        #     self.update_cache()
        return self.id

    def get_value_dict(self):
        values = dict()
        values['id'] = self.id_bin
        if self.name:
            values['name'] = self.name
        if self.description:
            values['description'] = self.description
        values['criteria_json'] = self.criteria_json
        values['blacklist_criteria_json'] = self.blacklist_criteria_json
        values['benefits_json'] = self.benefits_json
        un_hashed_string = unicode(self.criteria_json) + \
            unicode(self.blacklist_criteria_json) + unicode(self.benefits_json)
        values['sha2hash'] = hashlib.sha256(un_hashed_string).hexdigest()
        values['active'] = self.active
        if self.created_by:
            values['created_by'] = self.created_by
        if self.updated_by:
            values['updated_by'] = self.updated_by
        return values

    def __eq__(self, other):
        if self.criteria_obj == other.criteria_obj and self.blacklist_criteria_obj == other.blacklist_criteria_obj and self.benefits_obj == other.benefits_obj:

            return True
        return False

    @staticmethod
    def find_one(id, db=None):
        id = binascii.a2b_hex(id)
        if not db:
            db = CouponsAlchemyDB()
        rule_dict = db.find_one("rule", **{'id': id})
        if rule_dict:
            rule_dict['id'] = binascii.b2a_hex(rule_dict['id'])
            rule = Rule(**rule_dict)
            return rule
        return False

    def blacklist_items(self, order, code):

        if not self.blacklist_criteria_obj:
            return

        status, error = self.blacklist_criteria_obj.match_criteria(order, code)
        if status is MatchStatus.found_not_matching:
            return

        for item in order.items:
            if self.blacklist_criteria_obj.match_item(item) is MatchStatus.found_matching:
                item.blacklisted = True

    def match(self, order, voucher):

        for item in order.items:
            item.blacklisted = False

        self.blacklist_items(order, voucher.code)

        return self.criteria_obj.match(order, voucher)
