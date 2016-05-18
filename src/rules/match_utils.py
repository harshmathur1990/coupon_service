from lib.utils import get_intersection_of_lists
from lib.exceptions import UserNotFoundException


# All match methods accept first arguments as rule criteria and second as value to match
# (can be a order object in case of callback), Other optional argument can be a callback function

def match_value_in_list(list_of_elements, element):
    if element in list_of_elements:
        return True
    return False


def match_list_intersection_atleast_one_common(criteria_list, value_list):
    if get_intersection_of_lists(criteria_list, value_list):
        return True
    return False


def match_user_order_no(valid_on_order_no, order, fetch_user_order_detail_callback):
    exact_order_no_list = list()
    min_order_no = None
    for an_order_no in valid_on_order_no:
        try:
            # to convert order nos which are exact integers
            exact_order_no_list.append(int(an_order_no))
        except ValueError:
            # to convert order nos which are like 4+ means minimum order no 4
            if not min_order_no:
                min_order_no = int(an_order_no[:-1])

    if exact_order_no_list or min_order_no:
        # if minimum order no is given 1 (1+), than the condition is true always.
        # else fetch order details and check if the coupon is valid on
        # that particular order no
        if min_order_no and min_order_no is 1:
            return True
        else:
            success, order_no = fetch_user_order_detail_callback(order)
            if not success:
                raise UserNotFoundException()
            order_no += 1
            if (exact_order_no_list and order_no in exact_order_no_list) \
                    or (min_order_no and order_no >= min_order_no):
                return True
            else:
                return False


def match_in_not_in(criteria, value):
    if (criteria['in'] and get_intersection_of_lists(criteria['in'], value)) \
            or (criteria['not_in'] and not get_intersection_of_lists(criteria['not_in'], value)):
        return True
    else:
        return False

def match_greater_than(criteria, value):
    if value > criteria:
        return True
    return False


def match_less_than(criteria, value):
    if value < criteria:
        return True
    return False


def match_greater_than_equal_to(criteria, value):
    if value >= criteria:
        return True
    return False


def match_less_than_equal_to(criteria, value):
    if value <= criteria:
        return True
    return False
