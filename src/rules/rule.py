import uuid
import logging
import canonicaljson
import hashlib
import binascii
from src.enums import *
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
        self.rule_type = kwargs.get('rule_type')
        self.criteria_obj = kwargs.get('criteria_obj')
        self.criteria_json = kwargs.get('criteria_json')
        self.benefits_json = kwargs.get('benefits_json')
        self.benefits_obj = kwargs.get('benefits_obj')
        self.sha2hash = kwargs.get('sha2hash')
        self.active = kwargs.get('active', True)
        self.created_by = kwargs.get('created_by')
        self.updated_by = kwargs.get('updated_by')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        if not self.rule_type:
            self.get_rule_type()
        if not self.criteria_obj:
            criteria_dict = canonicaljson.json.loads(self.criteria_json)
            self.criteria_obj = RuleCriteria(**criteria_dict)
        if not self.benefits_obj:
            benefits_dict = canonicaljson.json.loads(self.benefits_json)
            self.benefits_obj = Benefits(**benefits_dict)

    def get_rule_type(self):
        self.rule_type = 0
        pass

    def save(self):
        values = self.get_value_dict()
        db = CouponsAlchemyDB()
        db.begin()
        try:
            # check if the rule being created already exists, if yes, just return rule id
            existing_rule = db.find_one("rule", **{'id': self.id_bin})
            if not existing_rule:
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
                    db.insert_row("rule", **values)
            else:
                # call is to update the existing rule with new attributes, just update and save it
                db.update_row("rule", 'id', **values)
        except Exception as e:
            logger.exception(e)
            db.rollback()
            return False
        else:
            db.commit()
        return self.id

    def get_value_dict(self):
        values = dict()
        values['id'] = self.id_bin
        if self.name:
            values['name'] = self.name
        if self.description:
            values['description'] = self.description
        values['rule_type'] = self.rule_type
        values['criteria_json'] = self.criteria_json
        values['benefits_json'] = self.benefits_json
        un_hashed_string = unicode(self.criteria_json) + \
                          unicode(self.benefits_json)
        values['sha2hash'] = hashlib.sha256(un_hashed_string).hexdigest()
        values['active'] = self.active
        if self.created_by:
            values['created_by'] = self.created_by
        values['updated_by'] = self.updated_by
        return values

    def __eq__(self, other):
        if self.criteria_obj == other.criteria_obj and \
                self.benefits_obj == other.benefits_obj:
            return True
        return False

    @staticmethod
    def find_one(id):
        db = CouponsAlchemyDB()
        rule_dict = db.find_one("rule", **{'id': id})
        rule = Rule(**rule_dict)
        return rule


class RuleCriteria(object):
    def __init__(self, **kwargs):
        self.area = kwargs.get('area', list())
        self.brands = kwargs.get('brands', list())
        self.categories = kwargs.get('categories', {"in": [], "not_in": []})
        self.channels = kwargs.get('channels', None)
        self.city = kwargs.get('city', list())
        self.country = kwargs.get('country', list())
        self.payment_modes = kwargs.get('payment_modes', list())
        self.products = kwargs.get('products', list())
        self.range_max = kwargs.get('range_max', None)
        self.range_min = kwargs.get('range_min', None)
        self.sellers = kwargs.get('sellers', list())
        self.state = kwargs.get('state', list())
        self.storefronts = kwargs.get('storefronts', list())
        use_type = kwargs.get('use_type', 0),
        no_of_uses_allowed_per_user = kwargs.get('no_of_uses_allowed_per_user', None)
        no_of_total_uses_allowed = kwargs.get('no_of_total_uses_allowed', None)
        self.usage = {
            'use_type': use_type,
            'no_of_uses_allowed_per_user': no_of_uses_allowed_per_user,
            'no_of_total_uses_allowed': no_of_total_uses_allowed
        }
        self.variants = kwargs.get('variants', list())
        self.zone = kwargs.get('zone', list())

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        return canonicaljson.encode_canonical_json(self.__dict__)


class Benefits(object):
    def __init__(self, **kwargs):
        self.maximum_discount = kwargs.get('max_discount', None)
        self.data = kwargs.get('data', list())

    def __eq__(self, other) :
        return self.__dict__ == other.__dict__

    def canonical_json(self):
        return canonicaljson.encode_canonical_json(self.__dict__)


class BenefitsData(object):
    def __init__(self, **kwargs):
        self.type = kwargs.get('type')
        self.value = kwargs.get('value')