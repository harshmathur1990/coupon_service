from api.v1.utils import is_validity_period_exclusive_for_freebie_vouchers
from api.v1.rule_criteria import RuleCriteria

method_dict = {
    'check_auto_benefit_exclusivity': is_validity_period_exclusive_for_freebie_vouchers,
    'criteria_class': RuleCriteria
}