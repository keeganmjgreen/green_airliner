from typing import Literal
from uuid import uuid1 as uuid

import pandas as pd

from src.modeling_objects import EvSpec
from src.utils.utils import KM_PER_MILE, mpge_to_kwh_per_km

VEHICLE_SPECS_CSV_PATH = "src/data/vehicle_specs.csv"

MPG_METRIC_TYPE = Literal[
    "epa_combined_cty_hwy_mpg",
    "epa_cty_mpg",
    "epa_hwy_mpg",
    "driver_mpg",
]


def get_ev_spec_from_df(
    vehicle_specs_df: pd.DataFrame,
    charging_power_limit_kw: float,
    mpg_metric: MPG_METRIC_TYPE = "epa_combined_cty_hwy_mpg",
) -> EvSpec:
    """Calculate EV specs averaged among those in the given vehicle specs DataFrame."""

    avg_discharge_rate_kwh_per_km = (
        vehicle_specs_df["driver_mpg"].apply(mpge_to_kwh_per_km).mean()
    )

    avg_battery_capacity_kwh = (
        vehicle_specs_df["epa_range_miles"]
        * KM_PER_MILE
        * vehicle_specs_df["epa_combined_cty_hwy_mpg"].apply(mpge_to_kwh_per_km)
    ).mean()

    ev_spec = EvSpec(
        DISCHARGE_RATE_KWH_PER_KM=avg_discharge_rate_kwh_per_km,
        BATTERY_CAPACITY_KWH=avg_battery_capacity_kwh,
        CHARGING_POWER_LIMIT_KW=charging_power_limit_kw,
    )
    return ev_spec


def get_ev_spec_from_make_model(
    make: str,
    model_substring: str,
    vehicle_specs_csv_path: str = VEHICLE_SPECS_CSV_PATH,
    **kwargs
) -> EvSpec:
    """Get calculated EV specs averaged among those of the given make and model substring in the
    vehicle specs DataFrame.
    """

    vehicle_specs_df = pd.read_csv(vehicle_specs_csv_path)

    vehicle_specs_df = vehicle_specs_df[
        (vehicle_specs_df["make"] == make)
        & (vehicle_specs_df["model"].str.contains(model_substring))
    ]

    ev_spec = get_ev_spec_from_df(vehicle_specs_df, **kwargs)

    ev_spec.EV_SPEC_ID = uuid()
    ev_spec.MAKE = make
    ev_spec.MODEL = model_substring
    ev_spec.YEAR = "<year>"

    return ev_spec


# ==================================================================================================
# Tesla

DUBAI_TAXI_CHARGING_POWER_LIMIT_KW = 22.0  # Hard-coded. # TODO: Replace/remove.


def _get_tesla_specs_from_model(
    model_substring: str,
    charging_power_limit_kw: float = DUBAI_TAXI_CHARGING_POWER_LIMIT_KW,  # TODO: Remove default.
    **kwargs
) -> EvSpec:
    return get_ev_spec_from_make_model(
        "Tesla",
        model_substring,
        charging_power_limit_kw=charging_power_limit_kw,
        **kwargs
    )


tesla_model_3 = _get_tesla_specs_from_model("Model 3")
tesla_model_s = _get_tesla_specs_from_model("Model S")
tesla_model_x = _get_tesla_specs_from_model("Model X")
tesla_model_y = _get_tesla_specs_from_model("Model Y")

# ==================================================================================================
