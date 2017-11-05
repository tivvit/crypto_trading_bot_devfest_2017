import json

import numpy as np
from functools import lru_cache


class TradeStats(object):
    def __init__(self, timestamp=None, open=None, close=None, high=None,
                 low=None, volume=None):
        """

        Args:
            timestamp (int)
            open (float):
            close (float):
            high (float):
            low (float):
            volume (float):
        """

        self.open = open
        self.close = close
        self.high = high
        self.low = low
        self.volume = volume
        self.timestamp = timestamp

        self.cache = {}

    def __str__(self):
        return json.dumps(self.to_dict(), sort_keys=True)

    def to_dict(self):
        """

        Returns:
            dict:
        """
        return {
            "open": self.open,
            "close": self.close,
            "high": self.high,
            "low": self.low,
            "volume": self.volume,
            "timestamp": self.timestamp,
        }

    @property
    @lru_cache()
    def ohlc_avg(self):
        return (self.high + self.low + self.close + self.open) / 4

    @property
    @lru_cache()
    def hlc_avg(self):
         return (self.high + self.low + self.close) / 3

    @property
    def hthlc(self):
        return self.high - self.hlc_avg

    @property
    def lthlc(self):
        return self.low - self.hlc_avg

    @property
    def htohlc(self):
        return self.high - self.ohlc_avg

    @property
    def ltohlc(self):
        return self.low - self.ohlc_avg

    @property
    def htl(self):
        return self.high - self.low


class SequenceStats(object):
    def __init__(self, sequence):
        self.sequence = sequence

    @property
    @lru_cache()
    def mean(self):
        return np.mean(self.sequence)

    @property
    def std(self):
        return np.std(self.sequence)

    @property
    def min(self):
        return np.min(self.sequence)

    @property
    def max(self):
        return np.max(self.sequence)

    @property
    def devs(self):
        return [i - self.mean for i in self.sequence]

    @property
    def abs_devs(self):
        return list(map(abs, self.devs))

    @property
    def positive_deviations(self):
        return list(filter(lambda x: x > 0, self.devs))

    @property
    def negative_deviations(self):
        return list(map(abs, filter(lambda x: x < 0, self.devs)))

    @property
    def positive_deviations_avg(self):
        positive_devs = self.positive_deviations
        return np.mean(positive_devs) if positive_devs else 1.

    @property
    def negative_deviations_avg(self):
        negative_devs = self.negative_deviations
        return np.mean(negative_devs) if negative_devs else 1.

    @property
    def deviation_ratio(self):
        """
        Which way is the mean skewed

        Returns:
            float:
                > 1 means positive deviation
                < 1 means negative deviation
                1 means no deviation
        """
        return self.positive_deviations_avg / self.negative_deviations_avg

    @property
    def count_weighted_deviation_ratio(self):
        pos_devs_cnt = len(self.positive_deviations)
        neg_devs_cnt = len(self.negative_deviations)
        return ((self.positive_deviations_avg * pos_devs_cnt) /
                (self.negative_deviations_avg * neg_devs_cnt))

    @property
    def monotone(self):
        if len(self.sequence) < 2:
            return True
        last = self.sequence[0]
        pos = self.sequence[0] <= self.sequence[1]
        for i in self.sequence[1:]:
            if i - last == 0:
                continue
            if (i - last > 0) != pos:
                return False
            last = i
        return True


class WeightedSequenceStats(SequenceStats):
    def __init__(self, sequence, weights):
        self.sequence = sequence
        self.weights = weights
        super().__init__(self.sequence)

    @property
    def weighted_mean(self):
        return np.average(self.sequence, weights=self.weights)

    @property
    def weighted_devs(self):
        return [((v - self.weighted_mean), self.weights[i]) for i, v
                in enumerate(self.sequence)]

    @property
    def positive_weighted_deviations(self):
        return list(filter(lambda x: x[0] > 0, self.weighted_devs))

    @property
    def negative_weighted_deviations(self):
        return list(map(lambda x: (abs(x[0]), x[1]),
                        filter(lambda x: x[0] < 0, self.weighted_devs)))

    @property
    def positive_weighted_deviations_avg(self):
        positive_devs = self.positive_weighted_deviations
        return np.average([i[0] for i in positive_devs],
                          weights=[i[1] for i in positive_devs]) \
            if positive_devs else 1.

    @property
    def negative_weighted_deviations_avg(self):
        negative_devs = self.negative_weighted_deviations
        return np.average([i[0] for i in negative_devs],
                          weights=[i[1] for i in negative_devs]) \
            if negative_devs else 1.

    @property
    def weighted_deviation_ratio(self):
        return (self.positive_weighted_deviations_avg /
                self.negative_weighted_deviations_avg)

    @property
    def weighted_deviation_weighted_ratio(self):
        return ((self.positive_weighted_deviations_avg *
                 sum([i[1] for i in self.positive_weighted_deviations])) /
                (self.negative_weighted_deviations_avg *
                 sum([i[1] for i in self.negative_weighted_deviations])))


class TradeSequenceStats(TradeStats, WeightedSequenceStats):
    def __init__(self, trades):
        """

        Args:
            trades (list[Trades]):

        """

        self.count = len(trades)
        self.prices = [i.price for i in trades]

        self._trades = trades

        TradeStats.__init__(self,
                            open=trades[0].price,
                            close=trades[-1].price,
                            high=max([t.price for t in trades]),
                            low=min([t.price for t in trades]),
                            volume=sum([t.size for t in trades]))
        WeightedSequenceStats.__init__(self,
                                       [i.price for i in trades],
                                       [i.size for i in trades])
