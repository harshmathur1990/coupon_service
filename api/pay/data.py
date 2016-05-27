class VerificationItemData(object):
    def __init__(self, **kwargs):
        self.category = kwargs.get('category')  # will be a list
        self.product = kwargs.get('product')
        self.vendor = kwargs.get('vendor')  # may not be required
        self.amount = kwargs.get('amount')
        self.blacklisted = False


class OrderData(object):
    def __init__(self, **kwargs):
        self.order_no = kwargs.get('order_no')
        self.order_id = kwargs.get('order_id')
        self.country = kwargs.get('country')  # list
        self.state = kwargs.get('state')  # can and will be treated as list ex: Haryana/Delhi
        self.city = kwargs.get('city')  # treated as list for same reason above
        self.area = kwargs.get('area')
        self.zone = kwargs.get('zone')  # list
        self.channel = kwargs.get('channel')
        self.items = kwargs.get('items')  # Items will be a list, although in pay (this) case it will contain only one element
        self.source = kwargs.get('source')
        self.total_price = 0.0
        for item in self.items:
            self.total_price += item.price
        self.customer_id = kwargs.get('customer_id')
        self.existing_vouchers = list()
        self.can_accommodate_new_vouchers = True
        self.failed_vouchers = list()
