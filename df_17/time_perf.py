import numpy as np


class TimePerf(object):
    def __init__(self):
        self.times = {}

    def perf(self, name, t):
        if name not in self.times:
            self.times[name] = [t]
        self.times[name].append(t)

    def report(self, final_time):
        for k, v in sorted(self.times.items()):
            print("{} {:.2f}% avg: {:.6f}s total: {:.6f}s".format(
                k, sum(v) / final_time * 100, np.mean(v), sum(v)))
