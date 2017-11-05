import numpy as np

from .history import HistoryDownloader
from .stats import WeightedSequenceStats
from .stats import TradeStats


class TimeFrameTradeStats(WeightedSequenceStats):
    def __init__(self, from_currency, to_currency, granularity, client=None,
                 no_download=False, start=None, end=None, samples=None,
                 do_not_check_time=False):
        self.granularity = granularity
        history = HistoryDownloader(from_currency, to_currency,
                                    client=client, no_download=no_download,
                                    granularity=granularity, start=start,
                                    end=end, samples=samples,
                                    do_not_check_time=do_not_check_time)
        self.trades = history.get_trades()
        self.samples = history.samples
        self.minute_samples = self.granularity / 60
        self.buffer = []
        self.avg_sum_cache = None

    def mean_ohlc(self):
        if not self.ready:
            return np.mean([i.ohlc_avg for i in self.trades])
        else:
            if not self.avg_sum_cache:
                self.avg_sum_cache = sum([i.ohlc_avg for i in self.trades])
            return self.avg_sum_cache / self.samples

    @property
    def norm_sequence(self):
        norm = self.trades[0].hlc_avg
        return [i.hlc_avg - norm for i in self.trades]

    @property
    def sequence(self):
        return [i.hlc_avg for i in self.trades]

    @property
    def weights(self):
        return [i.volume for i in self.trades]

    def aggregate_trades(self):
        return TradeStats(
            open=self.buffer[0].open,
            close=self.buffer[-1].close,
            high=max([i.high for i in self.buffer]),
            low=min([i.low for i in self.buffer]),
            volume=sum([i.volume for i in self.buffer]),
        )

    def feed_minute_stats(self, minute_stats):
        self.buffer.append(minute_stats)
        if len(self.buffer) >= self.minute_samples:
            self.trades.append(self.aggregate_trades())
            if self.avg_sum_cache:
                self.avg_sum_cache += sum([i.ohlc_avg for i in self.buffer])
                self.avg_sum_cache -= \
                    sum([i.ohlc_avg for i in self.trades[:-self.samples]])
            self.trades = self.trades[-self.samples:]
            self.buffer = []

    def get_trades(self):
        return self.trades

    @property
    def ready(self):
        return len(self.trades) == self.samples
