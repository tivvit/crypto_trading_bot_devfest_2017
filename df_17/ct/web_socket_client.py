import gdax
import sys
from .trade import Trade


class GdaxWebsocketClient(gdax.WebsocketClient):
    def set_product(self, product):
        if type(product) == list:
            self.product = product
        else:
            self.product = [product]

    def on_open(self):
        # self.url = "wss://ws-feed.gdax.com/"
        self.products = self.product
        self.trades = []

    def on_message(self, msg):
        trade = self.matches(msg)
        if trade:
            self.trades.append(trade)

    def matches(self, msg):
        if msg["type"] == "match":
            trade = Trade(price=msg["price"], size=msg["size"])
            print(str(trade))
            return trade

    def get_trades(self):
        trades = self.trades[:]
        self.trades = []
        return trades

    def on_close(self):
        print("Closed socket client {}".format(self.product))


def close_client(ws_client):
    def close(signal, frame):
        print("Going to close")
        ws_client.close()
        print("closed")
        sys.exit(0)

    return close
