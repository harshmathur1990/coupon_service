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


class ListConverter(BaseConverter):
    def to_python(self, value):
        return value.split(',')

    def to_url(self, values):
        return ','.join(BaseConverter.to_url(value)
                        for value in values)
