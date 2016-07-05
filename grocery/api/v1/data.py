class VerificationItemData(object):
    def __init__(self, **kwargs):
        self.item_id = kwargs.get('item_id')
        self.brand = kwargs.get('brand')
        self.category = kwargs.get('category') # will be a list
        self.product = kwargs.get('product')
        self.seller = kwargs.get('seller')
        self.storefront = kwargs.get('storefront')
        self.variant = kwargs.get('variant')
        self.price = kwargs.get('price')
        self.quantity = kwargs.get('quantity')
        self.subscription_id = kwargs.get('subscription_id')
        self.blacklisted = False


class OrderData(object):
    def __init__(self, **kwargs):
        self.order_no = kwargs.get('order_no')
        self.country = kwargs.get('country')  #list
        self.state = kwargs.get('state')  # can and will be treated as list ex: Haryana/Delhi
        self.city = kwargs.get('city')  # treated as list for same reason above
        self.area = kwargs.get('area')
        self.zone = kwargs.get('zone')  # list
        self.channel = kwargs.get('channel')
        self.items = kwargs.get('items')  # list of instances of VerificationItemData
        self.source = kwargs.get('source')
        self.payment_mode = kwargs.get('payment_mode')
        self.check_payment_mode = kwargs.get('check_payment_mode')
        self.order_id = kwargs.get('order_id')
        self.area_id = kwargs.get('area_id')
        self.order_date = kwargs.get('order_date')
        self.validate = kwargs.get('validate')
        self.total_price = 0.0
        for item in self.items:
            self.total_price += item.price * item.quantity
        self.customer_id = kwargs.get('customer_id')
        self.session_id = kwargs.get('session_id')
        self.existing_vouchers = list()
        self.can_accommodate_new_vouchers = True
        self.failed_vouchers = list()
        self.matching_criteria_total = 0.0
