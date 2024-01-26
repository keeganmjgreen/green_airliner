# TODO: Rework usage of `rng`?

import datetime as dt
from typing import Tuple

import numpy as np
import pandas as pd

from src.emulators.ev_taxis_emulator import TripsDemandDataset
from src.modeling_objects import Geofence


def generate_synthetic_TripsDemandDataset(
    n_trips: int,
    geofence: Geofence,
    requested_timestamp_bounds: Tuple[dt.datetime, dt.datetime],
    random_seed: int = 0,
) -> pd.DataFrame:
    rng = np.random.default_rng(random_seed)

    start_timestamp, end_timestamp = requested_timestamp_bounds
    duration = end_timestamp - start_timestamp

    requested_timestamp_ser = pd.Series(
        start_timestamp + duration * rng.uniform(size=n_trips),
        name="requested_timestamp",
    )

    origins = geofence.sample_locations(n_locations=n_trips)
    destinations = geofence.sample_locations(n_locations=n_trips)

    df = pd.concat(
        [
            requested_timestamp_ser,
            pd.DataFrame(
                [o.coords for o in origins], columns=["origin_lat", "origin_lon"]
            ),
            pd.DataFrame(
                [d.coords for d in destinations],
                columns=["destination_lat", "destination_lon"],
            ),
        ],
        axis="columns",
    )
    df = df.sort_values(by="requested_timestamp").reset_index(drop=True)
    df = df.rename_axis("id").reset_index()
    df["id"] = df["id"].astype(str)

    return TripsDemandDataset(df)
