import json
from .trade_decider import TradeDirection


class Transaction(object):
    def __init__(self, direction: TradeDirection) -> None:
        self.direction = direction

    def __repr__(self) -> str:
        return json.dumps({
            "direction": self.direction,
        })
