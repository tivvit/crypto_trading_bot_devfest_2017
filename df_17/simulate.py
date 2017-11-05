"""GDAX Trading simulator

Usage:
  train_lr.py [-zepd <file> -s --stop <stop> -a <after> -b <before> -c <cnt>]
  [--err-avg]
  train_lr.py (-h | --help)

Options:
  -d=FILE       Data path [default: /data/gdax/BTC-EUR_27_6_2017_200_days_min.json]
  -h --help     Show this screen.
  -v --version  Version
  -z --zmq      Use ZMQ async send
  -e --elastic  Use Elasticsearch
  -p --debug    Debug mode
  -s --stop=<stop>   Stop time (e.x. 1481416080)
  -a --after=<after>     After time
  -b --before=<before>   Before time
  -c --cnt=<cnt>     Sample count [default: 10000]
  --err-avg     Compute error of averages
"""

import time
from typing import Dict, List

import numpy as np
import ujson as json
from ct.open_trade import OpenTrade
from ct.product import Product
from ct.time_frame_trade_stats import TimeFrameTradeStats
from docopt import docopt
from simulate_tools import _init_zmq, update_trade_stats, _init_es, \
    send_to_es, performance_stats, get_prediction_err, TradeSimulator, \
    check_ready, error_average, time_frame_trade_stats_sim, trade
from time_perf import TimePerf

VERSION = "1.0.0"


def main() -> None:
    args = docopt(__doc__, version=VERSION)
    print("Reading data from file {}".format(args["-d"]))
    async_send = args["--zmq"]
    use_es = args["--elastic"]
    trade_sim = TradeSimulator(args["-d"])
    product = Product("BTC", "EUR")
    trade_stats = {
        "M2": time_frame_trade_stats_sim(product, 2),
        "M3": time_frame_trade_stats_sim(product, 3),
        "M5": time_frame_trade_stats_sim(product, 5),
        "M10": time_frame_trade_stats_sim(product, 10),
        "M15": time_frame_trade_stats_sim(product, 15),
        "M20": time_frame_trade_stats_sim(product, 20),
        "M30": time_frame_trade_stats_sim(product, 30),
        "M60": time_frame_trade_stats_sim(product, 60),
        "M120": time_frame_trade_stats_sim(product, 120),
        "M240": time_frame_trade_stats_sim(product, 240),
    }  # type: Dict[str, TimeFrameTradeStats]

    stats = {
        "buys": 0,
        "sells": 0,
        "profit": 0,
    }

    open_trades = []  # type: List[OpenTrade]
    pred_errs = get_prediction_err()

    if async_send:
        sender = _init_zmq()

    if use_es:
        es = _init_es()

    debug = False
    if args["--debug"]:
        debug = True

    es_stats = []
    all_ready = False

    stop_time = int(args["--stop"]) if args["--stop"] else None
    start_time = None
    end_time = None
    if stop_time:
        after_mins = int(args["--after"]) if args["--after"] else 60
        before_mins = int(args["--before"]) if args["--before"] else 60
        after_time = after_mins * 60
        before_time = before_mins * 60
        start_time = stop_time - before_time
        end_time = stop_time + after_time

    time_perf = TimePerf() if debug else None

    err_avg = args["--err-avg"]
    if err_avg:
        avg_stats = {i: [] for i in trade_stats.keys()}
        avg_stats_p = {i: [] for i in trade_stats.keys()}

    next_pred = []
    pred_err = {"predict_" + i: [] for i in trade_stats}
    pred_err.update({"predict_" + i + "_p": [] for i in trade_stats})

    epoch_start = time.time()
    cnt = int(args["--cnt"])
    print("Processing {} samples".format(cnt))
    print('-' * 10)

    # main loop start
    for M1 in trade_sim.get_minute(time_perf=time_perf):
        if not M1:
            break

        update_trade_stats(M1, trade_stats, time_perf=time_perf)

        all_ready = check_ready(all_ready, trade_stats, time_perf)
        if not all_ready:
            continue

        if err_avg:
            error_average(M1, avg_stats, avg_stats_p, time_perf, trade_stats)

        if start_time and M1.timestamp < start_time:
            continue

        if end_time and M1.timestamp > end_time:
            break

        if stop_time and M1.timestamp >= stop_time:
            pass

        # todo your code goes HERE
        # print(M1.close)
        # if M1.ohlc_avg > 100:
        #     print("buy")
        # print(trade_stats["M10"].sequence)
        if M1.timestamp == 1481416080:
            open_trades = trade(M1, trade_volume(), False, open_trades, stats)

        if M1.timestamp == 1481550720:
            open_trades = trade(M1, trade_volume(), True, open_trades, stats)


        s = time.time() if time_perf else None
        stat = {
            "10m_average": trade_stats["M10"].mean_ohlc(),
            "240m_average": trade_stats["M240"].mean_ohlc(),
            "30m_average": trade_stats["M30"].mean_ohlc(),
            "60m_average": trade_stats["M60"].mean_ohlc(),
            "open": M1.open,
            "close": M1.close,
            "high": M1.high,
            "low": M1.low,
            "timestamp": M1.timestamp,
            "ohlc": M1.ohlc_avg,
            "hlc": M1.hlc_avg,
            "_index": "cryptotrade",
            "_type": "trade",
        }

        if M1.open <= M1.close:
            stat["up"] = M1.ohlc_avg
        else:
            stat["down"] = M1.ohlc_avg
        if debug:
            time_perf.perf("struct", time.time() - s)

        if async_send:
            sender.send_string(json.dumps(stat))
        if use_es:
            es_stats.append(stat)
            es_stats = send_to_es(es, es_stats, time_perf)

        # End loop after n iterations
        cnt -= 1
        if cnt == 0:
            break

    print('-' * 10)

    if use_es:
        es_stats = send_to_es(es, es_stats, time_perf)

    if err_avg:
        for i in avg_stats:
            print("{}: average_error {:.6f} ({:.6f}%)".format(
                i, np.mean(avg_stats[i]), np.mean(avg_stats_p[i]) * 100))

    performance_stats(epoch_start, time_perf)

    for s in sorted(stats):
        print("{}: {}".format(s, stats[s]))


def trade_volume():
    """

    Returns:
        int: How much money you want to invest in the trade (EUR)
    """
    return 100


if __name__ == "__main__":
    main()
