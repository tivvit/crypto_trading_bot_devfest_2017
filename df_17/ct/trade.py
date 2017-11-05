import json


class Trade(object):
    """
        GDAX trade example:
         {'type': 'match', 'trade_id': 2816100,
         'maker_order_id': '52d3f5d9-833f-4382-865e-994de24fe1ed',
         'taker_order_id': '5a361b81-5216-4710-a126-e3bc559714f6',
         'side': 'sell', 'size': '0.02000000', 'price': '2382.78000000',
         'product_id': 'BTC-EUR', 'sequence': 2021968895,
         'time': '2017-06-17T22:48:39.104000Z'}
    """

    def __init__(self, price: float = None, size: float = None) -> None:
        self.price = float(price)
        self.size = float(size)

    @property
    def money(self) -> float:
        return self.price * self.size

    def __str__(self) -> str:
        return json.dumps({
            "price": self.price,
            "size": self.size,
            "money": self.money,
        }, sort_keys=True)
