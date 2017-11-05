class Product(object):
    def __init__(self, from_currency: str, to_currency: str) -> None:
        self.from_c = from_currency
        self.to_c = to_currency
        self.name = "{}-{}".format(self.from_c, self.to_c)