import binascii
import hashlib
import logging

import canonicaljson

from api.v1.data import OrderData
from api.v1.rule_criteria import RuleCriteria
from src.enums import UseType, BenefitType, MatchStatus
from src.sqlalchemydb import CouponsAlchemyDB

logger = logging.getLogger()


class Rule(object):

    def __init__(self, **kwargs):
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
            self.criteria_obj = RuleCriteria(**criteria_dict)
        if not self.blacklist_criteria_obj and self.blacklist_criteria_json is not None:
            blacklist_criteria_dict = canonicaljson.json.loads(self.blacklist_criteria_json)
            self.blacklist_criteria_obj = RuleCriteria(**blacklist_criteria_dict)
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
        if self.criteria_obj == other.criteria_obj and \
                self.benefits_obj == other.benefits_obj:
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

    def match(self, order, code):
        assert isinstance(order, OrderData)

        for item in order.items:
            item.blacklisted = False

        self.blacklist_items(order, code)

        return self.criteria_obj.match(order, code)


class Benefits(object):
    def __init__(self, **kwargs):
        self.max_discount = kwargs.get('max_discount', kwargs.get('maximum_discount', None))
        self.data = kwargs.get('data', list())
        self.data.sort()

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        return canonicaljson.encode_canonical_json(self.__dict__)


class BenefitsData(object):
    def __init__(self, **kwargs):
        self.type = kwargs.get('type')
        self.value = kwargs.get('value')
        if self.type == BenefitType.freebie.value:
            self.value.sort()