import numpy as np
import math

import time
from scipy import stats


class Predictor(object):
    """
    TODO:
    * https://stackoverflow.com/questions/27128688/how-to-use-least-squares-with-weight-matrix-in-python
    """

    def __init__(self, sequence):
        self.sequence = sequence


class LinearPredictorStats(Predictor):
    def __init__(self, sequence, time_perf=None):
        self.slope = None
        self.intercept = None
        self.r_value = None
        self.p_value = None
        # slope stderr
        self.std_err = None

        super().__init__(sequence)
        self.fit(time_perf=time_perf)

    def fit(self, time_perf=None):
        s = time.time() if time_perf else None
        self.slope, self.intercept, self.r_value, self.p_value, self.std_err = \
            stats.linregress(range(len(self.sequence)), self.sequence)
        if time_perf:
            time_perf.perf("fit", time.time() - s)
            # this is slower
            # from sklearn import linear_model.linear_model.LinearRegression()

    def predict(self, position=None, time_perf=None):
        """
        intercept + slope * x
        """
        s = time.time() if time_perf else None
        if not position:
            r = np.polyval((self.slope, self.intercept), len(self.sequence))
        else:
            r = np.polyval((self.slope, self.intercept), position)
        if time_perf:
            time_perf.perf("polyval", time.time() - s)
        return r

    @property
    def r_squared(self) -> float:
        return self.r_value ** 2

    @property
    def _devs(self):
        pred = self.predict(range(len(self.sequence)))
        correct_pred = zip(self.sequence, pred)
        return [(i - j) ** 2 for i, j in correct_pred]

    @property
    def mse(self):
        return sum(self._devs) / len(self.sequence)

    @property
    def std_dev(self):
        return math.sqrt(self.mse)


class LinearPredictor(Predictor):
    """
    Simple version of Linear predictor
    """

    def __init__(self, sequence, time_perf=None):
        self.slope = None
        self.intercept = None

        super().__init__(sequence)
        self.fit(time_perf=time_perf)

    def fit(self, time_perf=None):
        s = time.time() if time_perf else None
        l = len(self.sequence)
        self.slope, self.intercept = np.linalg.lstsq(
            [[i, 1] for i in range(l)], self.sequence)[0]
        if time_perf:
            time_perf.perf("predict.fit", time.time() - s)

    def predict(self, position=None, time_perf=None):
        """
        intercept + slope * x
        """
        s = time.time() if time_perf else None
        if not position:
            r = self.slope * len(self.sequence) + self.intercept
            # much slower
            # r = np.polyval((self.slope, self.intercept), len(self.sequence))
        else:
            r = self.slope * position + self.intercept
        if time_perf:
            time_perf.perf("predict.value", time.time() - s)
        return r


class PolyPredictor(Predictor):
    """
    TODO:
    * effective degree
    """

    def __init__(self, sequence, degree=1):
        self.std = None
        self.p = None
        self.residuals = None
        self.degree = degree
        super().__init__(sequence)
        self.fit()

    def fit(self):
        self.p, self.residuals, _, _, _ = np.polyfit(range(len(self.sequence)),
                                                     self.sequence,
                                                     self.degree,
                                                     full=True)

    def predict(self, position=None):
        if not position:
            return np.polyval(self.p, len(self.sequence))
        return np.polyval(self.p, position)

    @property
    def _devs(self):
        pred = self.predict(range(len(self.sequence)))
        correct_pred = zip(self.sequence, pred)
        return [(i - j) ** 2 for i, j in correct_pred]

    @property
    def mse(self):
        if self.residuals:
            return self.residuals / len(self.sequence)
        else:
            return sum(self._devs) / len(self.sequence)

    @property
    def std_dev(self):
        return math.sqrt(self.mse)
