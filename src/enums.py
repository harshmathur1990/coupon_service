from enum import Enum


class ItemType(Enum):
    not_available = 0
    product = 1
    category = 2
    sub_category = 3
    storefront = 4
    brand = 5
    variant = 6
    seller = 7


class UseType(Enum):
    not_available = 0
    global_use = 1
    per_user = 2
    both = 3


class LocationType(Enum):
    not_available = 0
    country = 1
    state = 2
    city = 3
    locality = 4


class BenefitType(Enum):
    amount = 0
    percentage = 1
    freebie = 2


class FreebieEntityType(Enum):
    variant = 0
    subscription = 1
