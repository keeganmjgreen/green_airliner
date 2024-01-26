from typing import Dict, List, Tuple
from uuid import uuid1 as uuid

import numpy as np

from src.modeling_objects import ID_TYPE, EvTaxi, EvSpec, Geofence


def generate_synthetic_evs_state(
    ev_specs: List[EvSpec],
    default_speed_kmph: float,
    initial_soc_bounds: Tuple[float, float],
    initial_geofence: Geofence,
    battery_efficiency: float = EvTaxi.BATTERY_EFFICIENCY,
    random_seed: int = 0,
) -> Dict[ID_TYPE, EvTaxi]:
    rng = np.random.default_rng(random_seed)

    evs_state = {}

    for i, ev_spec in enumerate(ev_specs):
        ev_id = str(uuid())
        evs_state[ev_id] = EvTaxi(
            ID=ev_id,
            DEFAULT_SPEED_KMPH=default_speed_kmph,
            **ev_spec.__dict__,
            soc=rng.uniform(*initial_soc_bounds),
            location=initial_geofence.sample_locations(n_locations=1)[0],
            BATTERY_EFFICIENCY=battery_efficiency,
        )

    return evs_state
