from typing import List

import gdax
import datetime
import math
import time
from .stats import TradeStats


class Granularity(object):
    SECOND = 1
    MINUTE = 60
    HOUR = MINUTE * 60
    DAY = HOUR * 24
    WEEK = DAY * 7


class HistoryDownloader(object):
    """
    """

    def __init__(self,
                 from_currency: str,
                 to_currency: str,
                 granularity: int,
                 client: gdax.PublicClient=None,
                 no_download: bool = False,
                 start: datetime.datetime = None,
                 end: datetime.datetime = None,
                 samples: int = None,
                 do_not_check_time: bool = False) -> None:
        self.hist = []
        self.product = "{}-{}".format(from_currency, to_currency)
        if not client:
            self.publicClient = gdax.PublicClient()
        else:
            self.publicClient = client
        self.max_points = 200
        self.max_downloads_per_sec = 5
        self.sleep_time = 1
        self.max_retries = 10
        self.granularity = granularity
        self.do_not_check_time = do_not_check_time
        self.samples = self._get_samples(samples=samples, start=start, end=end)
        if not no_download:
            self.download(granularity=self.granularity,
                          end=end,
                          start=start,
                          samples=self.samples)

    def _get_samples(self, samples=None, start=None, end=None):
        if start and end:
            samples_check = math.ceil((end - start).total_seconds() /
                                      self.granularity)
            if not samples:
                samples = samples_check
            elif samples_check != samples:
                print("Samples do not match {} != {}".format(samples,
                                                             samples_check))
            return samples
        elif not samples:
            raise Exception("Supply samples or start and end")
        return samples

    def download(self, granularity=None, end=None, start=None, samples=None):
        # todo extract to setters in init
        if not end:
            end = datetime.datetime.now()
        if not start:
            diff = datetime.timedelta(seconds=granularity * samples)
            start = end - diff

        if samples > self.max_points:
            # requested more data points than the api allows
            self.do_not_check_time = False
            parts = math.ceil(samples / self.max_points)
            part_time_frame = datetime.timedelta(
                seconds=granularity * self.max_points)
            for p in range(parts):
                print("Downloading {} of {}".format(p + 1, parts))
                # broaden the time windows (not losing data by rounding time)?
                part_start = start + (p * part_time_frame)
                part_end = part_start + part_time_frame
                if (p + 1) % self.max_downloads_per_sec == 0:
                    print("throttling")
                    time.sleep(self.sleep_time)
                if part_end > datetime.datetime.now():
                    part_end = datetime.datetime.now()
                self._download(part_start, part_end, granularity)
        else:
            self._download(start, end, granularity)

    def _download(self, start, end, granularity):
        samples = math.ceil((end - start).total_seconds() / granularity)
        print("Getting {} samples in [{} - {}]".format(
            samples,
            start.isoformat(),
            end.isoformat()))
        hist = None
        for i in range(self.max_retries):
            try:
                if i > 0:
                    print("Retry {}".format(i))
                hist = self._gdax_download(end, granularity, start)
                if "message" in hist:
                    # {'message': 'Rate limit exceeded'}
                    print(hist)
                    print("throttling, try {}".format(i))
                    time.sleep(self.sleep_time)
                elif hist and len(hist):
                    break
                else:
                    print("Strange response")
                    print(hist)
                    time.sleep(1)
            except Exception as e:
                print("ERR {}".format(e))
                time.sleep(1)
        if not hist:
            print("No data downloaded")
            return
            # raise Exception("No data downloaded")

        print("Got {} samples from [{} - {}]".format(
            len(hist),
            self._timestamp_to_isotime(hist[-1][0]),
            self._timestamp_to_isotime(hist[0][0])))
        part = list(reversed(hist[:samples]))
        if not self.do_not_check_time:
            part = list(filter(lambda x:
                               datetime.datetime.fromtimestamp(int(x[0])) >=
                               start, part))
        self.hist += part
        print("Stored {} samples from [{} - {}] actual size {}".format(
            len(part),
            self._timestamp_to_isotime(part[0][0]),
            self._timestamp_to_isotime(part[-1][0]),
            len(self.hist)))

        return {
            "end_time": datetime.datetime.fromtimestamp(int(part[-1][0]))
        }

    def _gdax_download(self, end, granularity, start):
        return self.publicClient.get_product_historic_rates(
            self.product,
            start=start.isoformat(),
            end=end.isoformat(),
            granularity=granularity)

    def get(self):
        return self.hist

    def get_trades(self) -> List[TradeStats]:
        """
            [ time, low, high, open, close, volume],
        """
        return [TradeStats(timestamp=i[0], low=i[1], high=i[2], open=i[3],
                           close=i[4], volume=i[5])
                for i in self.hist]

    @staticmethod
    def _timestamp_to_isotime(timestamp):
        return datetime.datetime.fromtimestamp(int(timestamp)).isoformat()
