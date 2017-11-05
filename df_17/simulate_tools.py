import time

import numpy as np
import zmq
import ujson as json
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk, streaming_bulk

from ct.history import Granularity
from ct.prediction import LinearPredictor
from ct.stats import TradeStats
from ct.time_frame_trade_stats import TimeFrameTradeStats


def _init_zmq():
    context = zmq.Context()
    # Socket to send messages on
    sender = context.socket(zmq.PUB)
    sender.bind("tcp://*:5557")
    sender.set_hwm(0)
    time.sleep(1)
    print("zmq inited")
    return sender


def update_trade_stats(M1, trade_stats, time_perf=None):
    s = time.time() if time_perf else None
    for k, ts in trade_stats.items():
        ts.feed_minute_stats(M1)
    if s:
        time_perf.perf("feed", time.time() - s)


def _init_es():
    es = Elasticsearch(hosts=["elasticsearch"])
    index = "cryptotrade"
    es.indices.create(index=index, ignore=400)
    mapping = json.dumps(
        {
            "properties": {
                "timestamp": {
                    "type": "long",
                    "copy_to": "@timestamp"
                },
                "@timestamp":
                    {
                        "type": "date",
                        "format": "epoch_second"
                    }
            }
        })
    es.indices.put_mapping(index=index, doc_type="trade",
                           body=mapping)
    es.indices.put_mapping(index=index, doc_type="predict",
                           body=mapping)
    return es


def send_to_es(es, es_stats, time_perf=None):
    if len(es_stats) >= 1000:
        try:
            failed = 0
            success = 0
            s = time.time() if time_perf else None
            for ok, result in streaming_bulk(
                    es,
                    es_stats,
                    raise_on_error=True,
                    raise_on_exception=True,
                    chunk_size=10000):
                if not ok:
                    failed += 1
                else:
                    success += 1
            if failed:
                print("Failed to index {} samples".format(failed))
            es_stats = []
            # es.index(index="cryptotrade", doc_type='trade', body=stat)
            if time_perf:
                time_perf.perf("elastic", time.time() - s)
        except Exception as e:
            print("ES err {}".format(e))
    return es_stats


def performance_stats(epoch_start, time_perf):
    running_time = time.time() - epoch_start
    print("Running time: {:.6f}s".format(running_time))
    if time_perf:
        time_perf.report(running_time)
        print()


def get_prediction_err(f="/app/prediction_error.json"):
    return json.load(open(f))


class TradeSimulator(object):
    def __init__(self, file_name):
        self.file_name = file_name
        self.f = open(self.file_name)

    def get_minute(self, time_perf=None):
        for i in self.f:
            if time_perf:
                s = time.time()
            t = json.loads(i)
            ts = TradeStats(open=float(t["open"]),
                            close=float(t["close"]),
                            high=float(t["high"]),
                            low=float(t["low"]),
                            volume=t["volume"],
                            timestamp=t["timestamp"])
            if time_perf:
                time_perf.perf("load_parse", time.time() - s)
            yield ts


def check_ready(all_ready, trade_stats, time_perf=None):
    s = time.time() if time_perf else None
    if all_ready:
        return True
    res = all([ts.ready for ts in trade_stats.values()])
    if time_perf:
        time_perf.perf("check", time.time() - s)
    return res


def predict(trade_stats, k=1, l=None, abs_shift=0, time_perf=None):
    seq = trade_stats.sequence
    p = LinearPredictor(seq, time_perf=time_perf)
    if not l:
        l = len(seq)
    return p.predict(position=(l * k) + abs_shift, time_perf=time_perf)


def predictions(M1, es_stats, trade_stats, predict_shift=1, pred_err=[],
                sources=["M2"], next_pred=[], time_perf=None, evaluate=False):
    s = time.time() if time_perf else None
    predictions = {
        "predict_" + i: predict(trade_stats[i], abs_shift=predict_shift,
                                time_perf=time_perf)
        for i in sources}  # type: Dict[str, float]
    predictions.update({
        "timestamp": M1.timestamp + (predict_shift * 60),
        "_index": "cryptotrade",
        "_type": "predict",
    })
    prediction_error(M1, next_pred, pred_err)
    if evaluate:
        next_pred.append(predictions)
    es_stats.append(predictions)
    if time_perf:
        time_perf.perf("predict", time.time() - s)
    return predictions


def error_average(M1, avg_stats, avg_stats_p, time_perf, trade_stats):
    s = time.time() if time_perf else None
    for i in trade_stats.keys():
        ts_avg = trade_stats[i].mean_ohlc()
        val = M1.ohlc_avg
        diff = abs(ts_avg - val)
        avg_stats[i].append(diff)
        avg_stats_p[i].append(diff / M1.ohlc_avg)
    if time_perf:
        time_perf.perf("avg_err", time.time() - s)


def prediction_error(m1, next_pred, pred_err):
    if not next_pred:
        return

    while next_pred:
        next_minute_pred = next_pred[0]
        if next_minute_pred["timestamp"] >= m1.timestamp:
            break
        next_pred.pop(0)
        if not next_pred:
            return

    if next_minute_pred["timestamp"] != m1.timestamp:
        # print("Not matching stamps {} {}".format(
        #     next_minute_pred["timestamp"], m1.timestamp))
        return

    for i in next_minute_pred:
        if not i.startswith("predict_"):
            continue
        if not np.isnan(next_minute_pred[i]):
            diff = abs(m1.ohlc_avg - next_minute_pred[i])
            pred_err[i].append(diff)
            pred_err[i + "_p"].append(diff / m1.ohlc_avg)


def time_frame_trade_stats_sim(product, samples):
    return TimeFrameTradeStats(product.from_c, product.to_c,
                               Granularity.MINUTE, samples=samples,
                               no_download=True)


def trade(M1, volume, buy, active_trade, stats, no_fee=False):
    FEE = 0.0025
    if no_fee:
        FEE = 0

    if active_trade:
        if "buy" in active_trade and buy:
            diff = active_trade["buy"] - M1.hlc_avg
            stats["sells"] += 1
            stats["profit"] += profit(diff, active_trade["volume"],
                                      active_trade["buy"], FEE)
        if "sell" in active_trade and not buy:
            diff = M1.hlc_avg - active_trade["sell"]
            stats["buys"] += 1
            stats["profit"] += profit(diff, active_trade["volume"],
                                      active_trade["sell"], FEE)
        if "sell" in active_trade and buy:
            diff = M1.hlc_avg - active_trade["sell"]
            stats["profit"] += profit(diff, active_trade["volume"],
                                      active_trade["sell"], FEE)
            return None
        if "buy" in active_trade and not buy:
            diff = active_trade["buy"] - M1.hlc_avg
            stats["profit"] += profit(diff, active_trade["volume"],
                                      active_trade["buy"], FEE)
            return None

    t = {
        "timestamp": M1.timestamp,
        "volume": volume,
        "_index": "cryptotrade",
        "_type": "trade1",
    }
    if buy:
        t.update({"buy": M1.ohlc_avg})
        stats["buys"] += 1
    else:
        t.update({"sell": M1.ohlc_avg})
        stats["sells"] += 1
    return t


def profit(diff, volume, price, fee):
    fee = 2 * fee * volume
    volume_r = volume / price
    share = diff * volume_r
    profit = share - fee
    print("Price diff: {:.4f}, Share: {:.4f}, fee: {:.4f}, "
          "Profit: {:.4f}".format(diff, share, fee, profit))
    return profit