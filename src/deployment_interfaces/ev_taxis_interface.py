import dataclasses
import datetime as dt
import os
from typing import Dict, Union

import pandas as pd
import requests

from src.modeling_objects import (
    CHARGE_POINT_ID_TYPE,
    CHARGING_SITE_ID_TYPE,
    CONNECTOR_ID_TYPE,
    EV_ID_TYPE,
    TRIP_ID_TYPE,
    TRIPS_DEMAND_FORECASTS_TYPE,
    AgentAction,
    ChargePoint,
    ChargingSite,
    Connector,
    EnvironmentState,
    EvTaxi,
    Location,
    Trip,
    TripsDemandForecast,
)
from src.projects import PROJECT_TYPE
from src.utils.utils import float_or_None, mpge_to_kwh_per_km

from .db_connections import LowVolDb
from .optimizer_dispatch import OptimizerDispatch
from .utils import IS_EMULATED_LOOKUP_BY_REALISM, REALISM_TYPE


@dataclasses.dataclass
class EvTaxisInterface:
    """A stand-in for the ``EvTaxisEmulator`` -- either the ``EvTaxisEmulator`` deployed elsewhere,
    or the real world.

    Allows the EV Taxis Optimizer component to get information about real and/or emulated assets
    (in method ``update_state``) and dispatch recommended actions for them (method ``set_action``).

    Is used in an environment, with an agent, to get the current state for that agent and set an
    action from that agent.

    To test, see the section
    "Running the Postgres database Docker container populated with mock data for testing the `EvTaxisInterface`"
    in ``README.md``.
    """

    PROJECT: PROJECT_TYPE
    ACCOUNT_ID: Union[int, None] = None
    REALISM: REALISM_TYPE = "emulated-assets-only"
    LOW_VOL_DB: Union[LowVolDb, None] = None
    NIFI_OPTIMIZER_DISPATCH_URL: str = os.getenv("NIFI_OPTIMIZER_DISPATCH_URL")
    current_state: EnvironmentState = dataclasses.field(init=False)

    def __post_init__(self):
        assert self.PROJECT is not None

        if self.ACCOUNT_ID is None:
            account_id = os.getenv("ACCOUNT_ID")
            if account_id is not None:
                self.ACCOUNT_ID = int(account_id)

        if self.LOW_VOL_DB is None:
            self.LOW_VOL_DB = LowVolDb()

    def update_state(self, timestamp: dt.datetime) -> None:
        """Update ``self.current_state: EnvironmentState`` by getting the EVs state and charging
        sites state from low-volume database, which includes both provisioning information and the
        last known states of assets.
        Also included in the ``EnvironmentState`` and low-volume database are the ongoing trips
        state and trips demand forecasts.

        The ``timestamp`` argument is unused for this.

        Delegates to methods ``_get_evs_state_from_db``, ``_get_charging_sites_state_from_db``,
        ``_get_flattened_connectors_state_from_db``, ``_get_ongoing_trips_state_from_db``, and
        ``_get_trips_demand_forecasts_from_db``.
        Each of those methods follows a more-or-less similar structure, first running a query and
        next constructing the state in question.
        """

        ongoing_trips_state = self._get_ongoing_trips_state_from_db()
        flattened_connectors_state = self._get_flattened_connectors_state_from_db()
        # ^ Both variables are assigned/saved here, used twice below, to query no more than once.

        # Construct the EnvironmentState:
        self.current_state = EnvironmentState(
            evs_state=self._get_evs_state_from_db(
                ongoing_trips_state, flattened_connectors_state
            ),
            charging_sites_state=self._get_charging_sites_state_from_db(
                flattened_connectors_state
            ),
            ongoing_trips_state=ongoing_trips_state,
            # trips_demand_forecasts=self._get_trips_demand_forecasts_from_db(),
        )

    def _get_evs_state_from_db(
        self,
        ongoing_trips_state: Dict[TRIP_ID_TYPE, Trip],
        flattened_connectors_state: Dict[CONNECTOR_ID_TYPE, Connector],
    ) -> Dict[EV_ID_TYPE, EvTaxi]:
        """Get EV taxis in their current state from low-volume database."""

        df = self.LOW_VOL_DB.query(
            """\
            WITH vehicle_info AS (
                SELECT
                    vehicle_id,
                    battery_capacity_kwh,
                    fuel_economy_mpge,
                    battery_soc_max,
                    max_plug_in_power_kw,
                    battery_efficiency_pc
                FROM common.vehicle_catalog 
                INNER JOIN common.vehicle
                ON common.vehicle_catalog.vehicle_catalog_id = common.vehicle.vehicle_catalog_id
            ),
            asset_last_state AS (
                SELECT
                    asset_id,
                    MAX(attribute_value) FILTER (
                        WHERE attribute_type = 'soc_pc'
                    ) AS soc_pc,
                    MAX(attribute_value) FILTER (
                        WHERE attribute_type = 'charge_status'
                    ) AS charge_status, -- TODO: Use this attribute?
                    MAX(attribute_value) FILTER (
                        WHERE attribute_type = 'plugged_in_connector_id'
                    ) AS plugged_in_connector_id
                FROM common.asset_last_state
                GROUP BY asset_id
            ),
            tmp1 AS (
                SELECT *
                FROM vehicle_info
                LEFT OUTER JOIN asset_last_state
                ON vehicle_info.vehicle_id = asset_last_state.asset_id
            ),
            asset AS (
                SELECT
                    asset_id,
                    name,
		            ST_Y(coordinates) AS lat,
                    ST_X(coordinates) AS lon,
                    account_id,
                    is_emulated
                FROM common.asset
            )
            SELECT *
            FROM tmp1
            INNER JOIN asset
            ON tmp1.vehicle_id = asset.asset_id
            """
        )
        df = self._filter_queried_df(df)

        evs_state = {
            row["vehicle_id"]: EvTaxi(
                DISCHARGE_RATE_KWH_PER_KM=mpge_to_kwh_per_km(
                    float(row["fuel_economy_mpge"])
                ),
                BATTERY_CAPACITY_KWH=float(row["battery_capacity_kwh"]),
                CHARGING_POWER_LIMIT_KW=float(row["max_plug_in_power_kw"]),
                ID=row["vehicle_id"],
                DEFAULT_SPEED_KMPH=...,
                soc=(float(row["soc_pc"]) / 100),
                location=Location(*row[["lat", "lon"]]),
                SOC_BOUNDS=(
                    float(row.get("battery_soc_min", EvTaxi.SOC_BOUNDS[0])) / 100,
                    float(row["battery_soc_max"]) / 100,
                ),
                BATTERY_EFFICIENCY=(float(row["battery_efficiency_pc"]) / 100),
                _trip=self._find_trip_assigned_to_ev(
                    ongoing_trips_state, ev_id=row["vehicle_id"]
                ),
                connector=(
                    flattened_connectors_state[row["plugged_in_connector_id"]]
                    if row["plugged_in_connector_id"] is not None
                    else None
                ),
            )
            for _, row in df.iterrows()
        }

        return evs_state

    @staticmethod
    def _find_trip_assigned_to_ev(
        ongoing_trips_state: Dict[TRIP_ID_TYPE, Trip], ev_id: EV_ID_TYPE
    ) -> Trip:
        """From the given ``ongoing_trips_state``, find the trip -- if any -- to which the EV of the
        given ``ev_id`` is assigned.

        Used by method ``_get_evs_state_from_db``.
        """

        assigned_trips = [
            t for t in ongoing_trips_state.values() if t.assigned_ev_id == ev_id
        ]

        if len(assigned_trips) == 0:
            return None
        elif len(assigned_trips) == 1:
            return assigned_trips[0]
        else:
            raise Exception(
                f"Taxi {ev_id} assigned to multiple trips "
                f"(trip IDs: {[t.ID for t in ongoing_trips_state]})."
            )

    def _get_charging_sites_state_from_db(
        self,
        flattened_connectors_state: Dict[CONNECTOR_ID_TYPE, Connector],
    ) -> Dict[CHARGING_SITE_ID_TYPE, ChargingSite]:
        """Get charging sites in their current state from low-volume database.

        Delegates to method ``_get_flattened_charge_points_state_from_db``.
        """

        if flattened_connectors_state is None:
            flattened_connectors_state = self._get_flattened_connectors_state_from_db()

        flattened_charge_points_state = self._get_flattened_charge_points_state_from_db(
            flattened_connectors_state
        )

        df = self.LOW_VOL_DB.query(
            """\
            WITH charging_site AS (
                SELECT
                    charging_site_id,
                    address
                FROM common.charging_site
            ),
            asset_last_state AS (
                SELECT
                    asset_id,
                    MAX(attribute_value) FILTER (
                        WHERE attribute_type = 'is_open'
                    ) AS is_open
                FROM common.asset_last_state
                GROUP BY asset_id
            ),
            tmp1 AS (
                SELECT *
                FROM charging_site
                LEFT OUTER JOIN asset_last_state
                ON charging_site.charging_site_id = asset_last_state.asset_id
            ),
            asset AS (
                SELECT
                    asset_id,
                    name,
                    description,
		            ST_Y(coordinates) AS lat,
                    ST_X(coordinates) AS lon,
                    account_id,
                    is_emulated
                FROM common.asset
            )
            SELECT *
            FROM tmp1
            INNER JOIN asset
            ON tmp1.charging_site_id = asset.asset_id
            """
        )
        df = self._filter_queried_df(df)

        # Assume, if not provided, that charging sites are open ('open for business') rather than
        #     closed (e.g., for maintenance):
        df["is_open"] = df["is_open"].fillna(True)

        charging_sites_state = {
            row["charging_site_id"]: ChargingSite(
                ID=row["charging_site_id"],
                NAME=row["name"],
                DESCRIPTION=row["description"],
                LAT=row["lat"],
                LON=row["lon"],
                charge_points={
                    cp.ID: cp
                    for cp in flattened_charge_points_state.values()
                    if cp.PARENT_CHARGING_SITE_ID == row["charging_site_id"]
                },
                ADDRESS=row["address"],
                is_open=row["is_open"],
            )
            for _, row in df.iterrows()
        }

        # If any charge points do not have location information, assume their location to be that of
        #     their parent charging site:
        for cp in flattened_charge_points_state.values():
            if cp.LAT is None or cp.LON is None:
                parent_charging_site = charging_sites_state[cp.PARENT_CHARGING_SITE_ID]
                cp.LAT, cp.LON = parent_charging_site.LAT, parent_charging_site.LON

        return charging_sites_state

    def _get_flattened_charge_points_state_from_db(
        self,
        flattened_connectors_state: Dict[CONNECTOR_ID_TYPE, Connector],
    ) -> Dict[CHARGE_POINT_ID_TYPE, ChargePoint]:
        """Get charge points in their current state from low-volume database."""

        if flattened_connectors_state is None:
            flattened_connectors_state = self._get_flattened_connectors_state_from_db()

        df = self.LOW_VOL_DB.query(
            """\
            WITH charge_point_catalog AS (
                SELECT
                    charge_point_catalog_id AS catalog_id,
                    charging_efficiency_pc,
                    hardware_charging_rate_limit_unit,
                    charging_mode
                FROM common.charge_point_catalog
            ),
            charge_point AS (
                SELECT
                    charge_point_id,
                    charging_site_id,
                    charge_point_catalog_id AS catalog_id,
                    hardware_charging_rate_limit
                FROM common.charge_point
            ),
            charge_point_info AS (
                SELECT *
                FROM charge_point_catalog
                INNER JOIN charge_point
                ON charge_point_catalog.catalog_id = charge_point.catalog_id
            ),
            asset_last_state AS (
                SELECT
                    asset_id,
                    MAX(attribute_value) FILTER (
                        WHERE attribute_type = 'is_open'
                    ) AS is_open
                FROM common.asset_last_state
                GROUP BY asset_id
            ),
            tmp1 AS (
                SELECT *
                FROM charge_point_info
                LEFT OUTER JOIN asset_last_state
                ON charge_point_info.charge_point_id = asset_last_state.asset_id
            ),
            asset AS (
                SELECT
                    asset_id,
                    name,
                    description,
		            ST_Y(coordinates) AS lat,
                    ST_X(coordinates) AS lon,
                    account_id,
                    is_emulated
                FROM common.asset
            )
            SELECT *
            FROM tmp1
            INNER JOIN asset
            ON tmp1.charge_point_id = asset.asset_id
            """
        )
        df = self._filter_queried_df(df)

        # Assert (for multi-connector charge points) that connectors operate in parallel rather than
        #     sequential (only-one-connector-simultaneously) charging mode:
        assert (df["charging_mode"] == "parallel").all()

        # Assume, if not provided, that charge points are open ('open for business') rather than
        #     closed (e.g., for maintenance):
        df["is_open"] = df["is_open"].fillna(True)

        flattened_charge_points_state = {
            row["charge_point_id"]: ChargePoint(
                ID=row["charge_point_id"],
                NAME=row["name"],
                DESCRIPTION=row["description"],
                LAT=row["lat"],
                LON=row["lon"],
                connectors={
                    c.ID: c
                    for c in flattened_connectors_state.values()
                    if c.PARENT_CHARGE_POINT_ID == row["charge_point_id"]
                },
                PARENT_CHARGING_SITE_ID=row["charging_site_id"],
                CHARGING_EFFICIENCY=(row["charging_efficiency_pc"] / 100),
                is_open=row["is_open"],
            )
            for _, row in df.iterrows()
        }

        # For each connector, fill-in its `PARENT_CHARGE_POINT_LOCATION` attribute (initialized to
        #     None) from its charge point's location:
        for cp in flattened_charge_points_state.values():
            for connector in cp.connectors.values():
                connector.PARENT_CHARGE_POINT_LOCATION = Location(cp.LAT, cp.LON)

        return flattened_charge_points_state

    def _get_flattened_connectors_state_from_db(
        self,
    ) -> Dict[CONNECTOR_ID_TYPE, Connector]:
        """Get charge point connectors in their current state from low-volume database."""

        df = self.LOW_VOL_DB.query(
            """\
            WITH connector_catalog AS (
                SELECT
                    charge_point_connector_catalog_id AS catalog_id,
                    hardware_charging_rate_limit_unit
                FROM common.charge_point_connector_catalog
                WHERE common.charge_point_connector_catalog.type = 'cable'
                -- ^ Just in case, even though the connector type should not be anything other than
                --     'cable' in EVFO Taxi Variant.
            ),
            connector AS (
                SELECT
                    charge_point_connector_id AS connector_id,
                    charge_point_connector_catalog_id AS catalog_id,
                    charge_point_id,
                    charging_site_id,
                    hardware_charging_rate_limit
                FROM common.charge_point_connector
            ),
            connector_info AS (
                SELECT *
                FROM connector_catalog
                INNER JOIN connector
                ON connector_catalog.catalog_id = connector.catalog_id
            ),
            asset_last_state AS (
                SELECT
                    asset_id,
                    MAX(attribute_value) FILTER (
                        WHERE attribute_type = 'is_plugged_in'
                    ) AS is_plugged_in
                FROM common.asset_last_state
                GROUP BY asset_id
            ),
            tmp1 AS (
                SELECT *
                FROM connector_info
                LEFT OUTER JOIN asset_last_state
                ON connector_info.connector_id = asset_last_state.asset_id
            ),
            asset AS (
                SELECT
                    asset_id,
                    name,
                    description,
                    account_id,
                    is_emulated
                FROM common.asset
            )
            SELECT *
            FROM tmp1
            INNER JOIN asset
            ON tmp1.connector_id = asset.asset_id
            """
        )
        df = self._filter_queried_df(df)

        # Assert only power-controlled charge points (the power delivered by current-controlled
        #     charge points requires the voltage of a parent circuit, which may not be provisioned
        #     in EVFO Taxi Variant):
        assert (df["hardware_charging_rate_limit_unit"] == "power_kW").all()

        flattened_connectors_state = {
            row["connector_id"]: Connector(
                ID=row["connector_id"],
                NAME=row["name"],
                DESCRIPTION=row["description"],
                CHARGING_POWER_LIMIT_KW=float(row["hardware_charging_rate_limit"]),
                PARENT_CHARGE_POINT_ID=row["charge_point_id"],
                PARENT_CHARGE_POINT_LOCATION=None,  # Will subsequently be filled-in.
                PARENT_CHARGING_SITE_ID=row["charging_site_id"],
                has_availability=row["is_plugged_in"],
            )
            for _, row in df.iterrows()
        }

        return flattened_connectors_state

    def _get_ongoing_trips_state_from_db(self) -> Dict[TRIP_ID_TYPE, Trip]:
        """Get ongoing requested trips in their current state from low-volume database.

        At the very least, this is done to determine which EV taxis are available to charge if they
        need to charge.
        """

        df = self.LOW_VOL_DB.query(
            """\
            SELECT
                requested_trip_id,
                requested_timestamp,
                pickup_timestamp,
                drop_timestamp,
                ST_Y(pickup_coordinates) AS pickup_lat,
                ST_X(pickup_coordinates) AS pickup_lon,
                ST_Y(drop_coordinates) AS drop_lat,
                ST_X(drop_coordinates) AS drop_lon,
                distance_km,
                vehicle_id,
                revenue
            FROM evfo_taxi.requested_trip
            WHERE drop_timestamp IS NULL -- Filters out trips that have been completed.
            -- Note: `distance_km` and `revenue` should be all-`NULL` in this query.
            """
        )

        ongoing_trips_state = {
            row["requested_trip_id"]: Trip(
                ID=row["requested_trip_id"],
                REQUESTED_TIMESTAMP=row["requested_timestamp"],
                ORIGIN=Location(*row[["pickup_lat", "pickup_lon"]]),
                DESTINATION=Location(*row[["drop_lat", "drop_lon"]]),
                distance_km=float_or_None(row["distance_km"]),
                assigned_ev_id=row["vehicle_id"],
                start_timestamp=row["pickup_timestamp"],
                end_timestamp=row["drop_timestamp"],
                revenue=float_or_None(row["revenue"]),
                # Note: `distance_km` and `revenue` should be `None` in this query.
            )
            for _, row in df.iterrows()
        }

        return ongoing_trips_state

    def _get_trips_demand_forecasts_from_db(self) -> TRIPS_DEMAND_FORECASTS_TYPE:
        """Get the latest trips demand forecasts from low-volume database."""

        df = self.LOW_VOL_DB.query(
            """\
            SELECT
                event_timestamp,
                ST_Y(bin_coordinates) AS bin_lat,
                ST_X(bin_coordinates) AS bin_lon,
                forecast_for_timestamp,
                n_trips_requested,
                revenue
            FROM evfo_taxi.forecast_by_bin
            WHERE event_timestamp = (
            	SELECT MAX(event_timestamp)
            	FROM evfo_taxi.forecast_by_bin
            ) -- Filter out all but the latest-made forecasts (maximum `event_timestamp`).
            """
        )

        trips_demand_forecasts = {
            fc_for_timestamp: []
            for fc_for_timestamp in df["forecast_for_timestamp"].unique()
        }  # (Initialized to dict of empty lists.)
        for _, row in df.iterrows():
            fc_for_timestamp = row["forecast_for_timestamp"]
            trips_demand_forecasts[fc_for_timestamp].append(
                TripsDemandForecast(
                    event_timestamp=row["event_timestamp"],
                    bin_location=Location(*row[["bin_lat", "bin_lon"]]),
                    forecast_for_timestamp=fc_for_timestamp,
                    n_trips_requested=float(row["n_trips_requested"]),
                    revenue=float(row["revenue"]),
                )
            )

        return trips_demand_forecasts

    def _filter_queried_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter assets from the DataFrame output of queries using the ``common.asset`` table of
        low-volume database.

        NOTE: Cannot be used with ``_get_ongoing_trips_state_from_db`` or
        ``_get_trips_demand_forecasts_from_db``.
        """

        # If an `ACCOUNT_ID` was given, use it to filter assets by the `account_id` column:
        if self.ACCOUNT_ID is not None:
            df = df[df["account_id"] == self.ACCOUNT_ID]
        # ^ TODO: Necessary given separation of logical databases per-account/customer? Remove?

        # If a `REALISM` was given, use it to filter assets by the `is_emulated` column:
        df = df[df["is_emulated"].isin(IS_EMULATED_LOOKUP_BY_REALISM[self.REALISM])]
        # ^ TODO: Necessary? Remove?

        return df

    def set_action(self, action: AgentAction) -> None:
        optimizer_dispatch = OptimizerDispatch(
            recommendedActions=action.to_asset_actions(), strategyType="smart"
        )
        json_optimizer_dispatch = optimizer_dispatch.to_json()
        requests.post(
            self.NIFI_OPTIMIZER_DISPATCH_URL, json=json_optimizer_dispatch
        )
