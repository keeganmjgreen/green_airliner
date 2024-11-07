import datetime as dt
from typing import List

import numpy as np
import scipy as sp

from src.three_d_sim.config_model import Timepoint

J_PER_MJ = 1e6
J_PER_WH = 3600
KM_PER_MILE = 1.609344
L_PER_CUBIC_M = 1000
M_PER_KM = 1000
MINUTES_PER_HOUR = SECONDS_PER_MINUTE = 60
MJ_PER_GJ = 1000
SECONDS_PER_HOUR = 3600
W_PER_KW = 1000
MJ_PER_KWH = W_PER_KW * J_PER_WH / J_PER_MJ

timedelta_to_minutes = lambda timedelta: timedelta / dt.timedelta(minutes=1)

sind = lambda angle_deg: np.sin(np.deg2rad(angle_deg))
cosd = lambda angle_deg: np.cos(np.deg2rad(angle_deg))


def get_interpolator_by_elapsed_time(points: List[Timepoint]):
    def interpolator(elapsed_mins: float):
        _interpolator = sp.interpolate.interp1d(
            x=[p.elapsed_mins for p in points],
            y=[p.value for p in points],
            bounds_error=False,
            fill_value=(points[0].value, points[-1].value),
        )
        y = _interpolator(elapsed_mins)
        return float(y)

    return interpolator
