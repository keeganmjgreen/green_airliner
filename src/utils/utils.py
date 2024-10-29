import datetime as dt
import os
import uuid
from typing import Any, Dict, Literal, Optional, List, Tuple, Union

import numpy as np
import pandas as pd
import pytz
import scipy as sp

MINUTES_PER_HOUR = SECONDS_PER_MINUTE = 60
SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR
MILLISECONDS_PER_SECOND = 1000

timedelta_to_minutes = lambda timedelta: timedelta.total_seconds() / SECONDS_PER_MINUTE

J_PER_MJ = 1e6
J_PER_WH = SECONDS_PER_HOUR
KWH_PER_MWH = 1000

M_PER_KM = 1000

KWH_PER_GALLON_GASOLINE = 33.7
KM_PER_MILE = 1.609344

mpge_to_kwh_per_km = lambda mpge: (KWH_PER_GALLON_GASOLINE / KM_PER_MILE) / mpge
kwh_per_km_to_mpge = lambda kwh_per_km: (KWH_PER_GALLON_GASOLINE / KM_PER_MILE) / kwh_per_km

sind = lambda angle_deg: np.sin(np.deg2rad(angle_deg))
cosd = lambda angle_deg: np.cos(np.deg2rad(angle_deg))


def invert_dict(d: Dict) -> Dict:
    """Swap keys and values of a Python dictionary."""
    values = d.values()
    assert len(values) == len(set(values))
    return {v: k for k, v in d.items()}


def _getenv(
    env_var_name: str,
    _type: type = str,
    handling: Literal[None, "raise"] = None,
    default_val: Optional[Any] = None,
) -> Union[Any, None]:
    """Thin wrapper of `os.getenv` with added functionality.

    Args:
        env_var_name (str): Name of the environment variable.
        _type (type, optional): Type to cast the environment variable to (if environment variable is
            not None). Defaults to str (no typecasting).
        handling (Literal[None, "warn", "raise"], optional): Whether to do nothing or raise an
            exception if environment variable is None (is unset OR zero-length string). Defaults to
            None to do nothing.
        default_val (Optional[Any], optional): Default value to use if the environment variable is
            None. Defaults to None.

    Returns:
        Union[Any, None]: The environment variable's value.
    """

    env_var = os.getenv(env_var_name)
    if env_var == "":
        env_var = None
    if env_var is None:
        msg = f"Environment variable {env_var_name} is unset or zero-length string."
        if handling == "raise":
            raise Exception(msg)
        env_var = default_val
    if env_var is not None:
        if _type is bool:
            env_var = {"true": True, "false": False}[env_var]
        else:
            env_var = _type(env_var)
    return env_var


def get_DATA_DIR() -> str:
    """Get the data directory (`DATA_DIR`) environment variable.

    If running locally (outside a Docker container), `DOCKER_DATA_DIR` (from the `Dockerfile`)
    should be None and `DATA_DIR` (set in your `.env` file) will be returned.
    If running in a Docker container, `DOCKER_DATA_DIR` should be non-None and is returned
    (`DATA_DIR` is ignored).
    """

    DATA_DIR = os.getenv("DATA_DIR")
    DOCKER_DATA_DIR = os.getenv("DOCKER_DATA_DIR")
    if DOCKER_DATA_DIR is not None and DOCKER_DATA_DIR != "":
        return DOCKER_DATA_DIR
    else:
        assert DATA_DIR is not None and DATA_DIR != ""
        return DATA_DIR


CHARGING_STATUS_CANONICAL_TYPE = {
    "PLUGGED_IN.CHARGING": 200,
    "PLUGGED_IN.NOT_CHARGING": 201,
    "NOT_PLUGGED_IN": 202,
}

to_datetime = lambda x: x.to_pydatetime() if type(x) is pd.Timestamp else x

datetime_to_utc_string = (
    lambda x: to_datetime(x).astimezone(pytz.utc).isoformat().replace("+00:00", "Z")
)

now = dt.datetime.now(tz=pytz.utc)

float_or_None = lambda x: float(x) if x is not None else x
"""Cast argument to float if not None."""

uuid_from_seed = lambda seed: uuid.UUID(int=abs(hash(seed)))
"""Create a UUID that is one-to-one with the given ``seed``, which may be any hashable object, such
as an ``int`` or ``str``.
"""


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
