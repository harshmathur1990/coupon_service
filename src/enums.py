from enum import Enum


class UseType(Enum):
    not_available = 0
    global_use = 1
    per_user = 2
    both = 3


class BenefitType(Enum):
    amount = 0
    percentage = 1
    freebie = 2
    pay_cashback = 101


class Channels(Enum):
    app = 0
    website = 1


class VoucherTransactionStatus(Enum):
    in_progress = 0
    success = 1
    failure = 2


class VoucherType(Enum):
    auto_freebie = 0
    regular_freebie = 1
    regular_coupon = 2


class SchedulerType(Enum):
    daily = 0
    exact = 1
    cron = 2


class MatchStatus(Enum):
    found_matching = 0
    found_not_matching = 1
    not_found = 2


class Permission(Enum):
    no_permission_required = 0
    create_voucher = 1
    update_voucher = 2
    check_voucher = 3
    apply_voucher = 4
    fetch_voucher = 5
    update_order_status = 6
    test = 7
