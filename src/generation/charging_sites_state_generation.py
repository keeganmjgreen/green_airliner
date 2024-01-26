"""Functions to create stateful charging site objects."""

from typing import Dict, List, Tuple
from uuid import uuid1 as uuid

import numpy as np
import pandas as pd

from src.modeling_objects import (
    CHARGING_SITE_ID_TYPE,
    ChargePoint,
    ChargingSite,
    Connector,
    Location,
)


def charging_sites_state_from_connectors_df(
    connectors_df: pd.DataFrame,
    ids_to_uuids: bool = False,
) -> Dict[CHARGING_SITE_ID_TYPE, ChargingSite]:
    """Construct charging site objects by converting from a DataFrame of charging sites' charge
    points' connectors.

    Args:
        connectors_df (pd.DataFrame): The DataFrame, with the following columns:
            charging_site_id
            charge_point_id
            lat
            lon
            connector_id
            connector_power_limit_kw
        ids_to_uuids (bool, optional): Whether to map each of charging site IDs, charge point IDs,
            and connector IDs to UUIDs. Defaults to False.
    """

    if ids_to_uuids:
        for id_col in ["charging_site_id", "charge_point_id", "connector_id"]:
            ids = connectors_df[id_col].unique()
            id_to_uuid_mapping = {id: str(uuid()) for id in ids}
            connectors_df[id_col] = connectors_df[id_col].map(id_to_uuid_mapping)

    charging_sites = {}
    for charging_site_id in connectors_df["charging_site_id"].unique():
        charging_site_df = connectors_df.set_index("charging_site_id").loc[
            [charging_site_id]
        ]
        charge_points = {}
        for charge_point_id in charging_site_df["charge_point_id"].unique():
            charge_point_df = charging_site_df.set_index("charge_point_id").loc[
                [charge_point_id]
            ]
            charge_point_coords = charge_point_df[["lat", "lon"]].mean().to_numpy()
            connectors = {}
            for connector_id in charge_point_df["connector_id"]:
                connectors[connector_id] = Connector(
                    ID=connector_id,
                    CHARGING_POWER_LIMIT_KW=charge_point_df.set_index(
                        "connector_id"
                    ).loc[connector_id]["connector_power_limit_kw"],
                    PARENT_CHARGE_POINT_ID=charge_point_id,
                    PARENT_CHARGE_POINT_LOCATION=Location(*charge_point_coords),
                    PARENT_CHARGING_SITE_ID=charging_site_id,
                )
            charge_points[charge_point_id] = ChargePoint(
                ID=charge_point_id,
                LAT=charge_point_coords[0],
                LON=charge_point_coords[1],
                connectors=connectors,
                PARENT_CHARGING_SITE_ID=charging_site_id,
            )
        charging_sites[charging_site_id] = ChargingSite(
            ID=charging_site_id,
            LAT=charging_site_df.groupby("charge_point_id")["lat"].mean().mean(),
            LON=charging_site_df.groupby("charge_point_id")["lon"].mean().mean(),
            charge_points=charge_points,
        )
    return charging_sites


def generate_charging_sites_state(
    sites_lat_lon_list: List[Tuple[float, float]],
    charge_points_per_site: int,
    connectors_per_charge_point: int,
    charging_power_limit_kw: float,  # TODO: Rename?
) -> Dict[CHARGING_SITE_ID_TYPE, ChargingSite]:
    """Generate charging site objects given this function's arguments."""

    # Currently assumes all charging sites to have availability in the initial charge points state.

    display_radius = 0.005
    display_angles = np.arange(
        start=0, stop=(2 * np.pi), step=(2 * np.pi / charge_points_per_site)
    )

    charging_sites = {}
    for charging_site_id, lat_lon in enumerate(sites_lat_lon_list):
        # For each charging site:
        charge_points = {}
        for _charge_point_id, angle in enumerate(display_angles):
            # For each charge point at that charging site:
            charge_point_id = charging_site_id + _charge_point_id
            charge_point_location = Location(
                *(lat_lon + display_radius * np.array([np.cos(angle), np.sin(angle)]))
            )
            connectors = {}
            for _connector_id in range(connectors_per_charge_point):
                # For each connector of that charge point:
                connector_id = charge_point_id + _connector_id
                connectors[str(_connector_id)] = Connector(
                    ID=str(connector_id),
                    CHARGING_POWER_LIMIT_KW=charging_power_limit_kw,
                    PARENT_CHARGE_POINT_ID=str(charge_point_id),
                    PARENT_CHARGE_POINT_LOCATION=charge_point_location,
                    PARENT_CHARGING_SITE_ID=str(charging_site_id),
                )
            charge_points[str(charge_point_id)] = ChargePoint(
                ID=str(charge_point_id),
                *charge_point_location.coords,
                connectors=connectors,
                PARENT_CHARGING_SITE_ID=str(charging_site_id),
            )
        charging_sites[str(charging_site_id)] = ChargingSite(
            ID=str(charging_site_id),
            LAT=lat_lon[0],
            LON=lat_lon[1],
            charge_points=charge_points,
        )
    return charging_sites
