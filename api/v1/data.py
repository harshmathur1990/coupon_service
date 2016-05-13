class VerificationItemData(object):
    def __init__(self, **kwargs):
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
        self.total_price = 0.0
        for item in self.items:
            self.total_price += item.price * item.quantity
        self.customer_id = kwargs.get('customer_id')
        self.existing_vouchers = list()
        self.can_accommodate_new_vouchers = True
        self.failed_vouchers = list()
