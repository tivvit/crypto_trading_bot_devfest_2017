from enum import Enum


class TradeDirection(Enum):
    buy = 1
    sell = -1
    none = 0


class TradeDecider(object):
    def __init__(self,
                 actual_price: float,
                 predicted_price: float,
                 fee: float,
                 size: int,
                 prediction_std: float,
                 price_std: float) -> None:
        self.fee = fee
        self.actual_price = actual_price
        self.predicted_price = predicted_price
        self.size = size
        self.prediction_std = prediction_std
        self.price_std = price_std
        # todo conf

    @property
    def raw_profit(self) -> float:
        return abs(self.actual_price - self.predicted_price)

    @property
    def product_part(self) -> float:
        return self.size / self.actual_price

    @property
    def sized_raw_profit(self) -> float:
        return self.product_part * self.raw_profit

    @property
    def actual_fee(self) -> float:
        return self.size * self.fee

    @property
    def profit(self) -> float:
        return self.sized_raw_profit - (2 * self.actual_fee)

    @property
    def uncertainty(self) -> float:
        return self.prediction_std  # + self.price_std

    @property
    def direction(self) -> TradeDirection:
        return TradeDirection.sell if self.actual_price > self.predicted_price \
            else TradeDirection.buy

    def decide(self) -> TradeDirection:
        if self.raw_profit > self.uncertainty and \
                        self.raw_profit > self.price_std and \
                        self.profit > 0:
            return self.direction
        return TradeDirection.none

    def __str__(self) -> str:
        return "{:.4f} +-{:.4f}".format(self.profit, self.uncertainty)

# class ShortTimeTradeDecider(TradeDecider):
#     def __init__(self, fee):
#         super().__init__(fee)
#
#     def trade(self) -> TradeDirection:
#         return TradeDirection.nothing
