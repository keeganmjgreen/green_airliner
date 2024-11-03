import datetime as dt
from typing import List, Tuple

import numpy as np
import scipy as sp

MINUTES_PER_HOUR = SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR
MILLISECONDS_PER_SECOND = 1000

timedelta_to_minutes = lambda timedelta: timedelta.total_seconds() / SECONDS_PER_MINUTE

J_PER_MJ = 1e6
MJ_PER_GJ = 1000
J_PER_WH = SECONDS_PER_HOUR
KWH_PER_MWH = 1000

L_PER_CUBIC_M = 1000

M_PER_KM = 1000

KWH_PER_GALLON_GASOLINE = 33.7
KM_PER_MILE = 1.609344

mpge_to_kwh_per_km = lambda mpge: (KWH_PER_GALLON_GASOLINE / KM_PER_MILE) / mpge
kwh_per_km_to_mpge = lambda kwh_per_km: (KWH_PER_GALLON_GASOLINE / KM_PER_MILE) / kwh_per_km

sind = lambda angle_deg: np.sin(np.deg2rad(angle_deg))
cosd = lambda angle_deg: np.cos(np.deg2rad(angle_deg))


def get_interpolator_by_elapsed_time(points: List[Tuple[float, float]]):
    def interpolator(elapsed_time: dt.timedelta):
        _interpolator = sp.interpolate.interp1d(
            *np.array(points).T,
            bounds_error=False,
            fill_value=(points[0][1], points[-1][1]),
        )
        y = _interpolator(timedelta_to_minutes(elapsed_time))
        return y

    return interpolator
