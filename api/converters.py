import binascii
from werkzeug.routing import BaseConverter


class HexConverter(BaseConverter):

    def to_python(self, value):
        try:
            binascii.a2b_hex(value)
            return value
        except:
            return None

    def to_url(self, values):
        try:
            binascii.a2b_hex(values)
            return values
        except:
            return None
