import json
from enum import Enum

from .trade_decider import TradeDirection


class TradeAction(Enum):
    close = 1
    nothing = 0


class OpenTrade(object):
    def __init__(self, open_price: float, volume: float,
                 direction: TradeDirection,
                 pred_price: float, fee: float, stop_loss: float = None) -> \
            None:
        self.open = open_price
        self.volume = volume
        self.direction = direction
        self.fee = fee
        self.predicted_price = pred_price
        self.fee = OpenTrade.fee(self.volume, self.fee)
        if self.direction == TradeDirection.buy:
            self.predicted_profit = self.predicted_price - self.open
        else:
            self.predicted_profit = self.open - self.predicted_price
        self.predicted_profit -= (2 * self.fee)
        self.stop_loss = 0.4
        if stop_loss:
            self.stop_loss = stop_loss
        direction_coef = 1 if self.direction == TradeDirection.buy else -1
        # todo - dependent on volume too much
        self.stop_loss_limit = self.open - (direction_coef * self.stop_loss * \
                                            self.volume)
        self.closed = False
        self.profit = -self.fee
        self.error = .0
        self.sl = False

    def __repr__(self) -> str:
        return json.dumps({
            "open": self.open,
            "volume": self.volume,
            "direction": self.direction,
            "stop_loss": self.stop_loss_limit,
            "predicted_profit": self.predicted_profit,
            "closed": self.closed,
        })

    def check(self, actual_price: float) -> TradeAction:
        # stop loss checks
        if self.direction == TradeDirection.buy and \
                        self.stop_loss_limit > actual_price:
            # todo is it ?
            self.sl = True
            self.close(actual_price)
            return TradeAction.close
        if self.direction == TradeDirection.sell and \
                        self.stop_loss_limit < actual_price:
            # todo is it ?
            self.sl = True
            self.close(actual_price)
            return TradeAction.close
        return TradeAction.nothing

    def close(self, actual_price: float) -> float:
        self.closed = True
        if self.direction == TradeDirection.buy:
            profit = actual_price - self.open
        else:
            profit = self.open - actual_price
        self.profit += profit
        self.profit -= self.fee
        self.error = self.profit - self.predicted_profit
        print("Closing trade start {:.4f} end {:.4f} with sl {:.4f} op {} "
              "predicted profit {:.4f} "
              "real profit {:.4f} fees {} sl {}"
              "".format(self.open, actual_price, self.stop_loss_limit,
                        self.direction, self.predicted_profit, self.profit,
                        2 * self.fee, self.sl))
        return self.profit

    def describe(self):
        print("Trade for {} predicted profit {}".format(self.direction,
                                                        self.predicted_profit))

    @staticmethod
    def fee(size: float, fee: float) -> float:
        return size * fee
