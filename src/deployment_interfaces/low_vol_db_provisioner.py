import dataclasses
import os
from typing import Any, Dict, List, Optional, Union
from uuid import uuid1 as uuid

import pandas as pd
import sqlalchemy

from src.modeling_objects import (
    CHARGE_POINT_ID_TYPE,
    CHARGING_SITE_ID_TYPE,
    CONNECTOR_ID_TYPE,
    EV_ID_TYPE,
    ChargePoint,
    ChargingSite,
    Connector,
    EnvironmentState,
    EvSpec,
    EvTaxi,
)
from src.projects import PROJECT_TYPE
from src.utils.utils import kwh_per_km_to_mpge

from .db_connections import LowVolDb


@dataclasses.dataclass
class LowVolDbProvisioner:
    PROJECT: PROJECT_TYPE
    ACCOUNT_ID: Union[int, None] = None
    LOW_VOL_DB: Union[LowVolDb, None] = None

    SQLALCHEMY_ENGINE: sqlalchemy.Engine = dataclasses.field(init=False)

    def __post_init__(self):
        assert self.PROJECT is not None

        if self.ACCOUNT_ID is None:
            account_id = os.getenv("ACCOUNT_ID")
            if account_id is not None:
                self.ACCOUNT_ID = int(account_id)

        if self.LOW_VOL_DB is None:
            self.LOW_VOL_DB = LowVolDb()

        self.SQLALCHEMY_ENGINE = self.LOW_VOL_DB.create_sqlalchemy_engine()

    def clear_low_vol_db_provisioning(self) -> None:
        """
        WARNING: Currently clears ALL low-volume database provisioning -- not only that provisioned
        by method ``provision_low_vol_db``.
        """
        self.LOW_VOL_DB.query(
            """\
            TRUNCATE
                common.vehicle,
                common.vehicle_catalog,
                common.charge_point_connector,
                common.charge_point_connector_catalog,
                common.charge_point,
                common.charge_point_catalog,
                common.charging_site,
                common.asset
            CASCADE
            """,
            output=False,
        )

    def provision_low_vol_db(
        self, state: EnvironmentState, ev_specs: Optional[List[EvSpec]] = None
    ) -> None:
        # EVs:
        self._provision_vehicles(evs_state=state.evs_state, ev_specs=ev_specs)

        # Charging sites:
        self._provision_charging_sites(charging_sites_state=state.charging_sites_state)

        # Charge points:
        flattened_charge_points_state = {
            cp.ID: cp
            for cs in state.charging_sites_state.values()
            for cp in cs.charge_points.values()
        }
        self._provision_charge_points(flattened_charge_points_state)

        # Connectors:
        flattened_connectors_state = {
            c.ID: c
            for cp in flattened_charge_points_state.values()
            for c in cp.connectors.values()
        }
        self._provision_connectors(flattened_connectors_state)

    def _provision_vehicles(
        self,
        evs_state: Dict[EV_ID_TYPE, EvTaxi],
        ev_specs: Optional[List[EvSpec]] = None,
    ) -> None:
        # In `common.vehicle_catalog` table...
        assert ev_specs is not None, "Not yet supported."
        vehicle_catalog_list = []
        for ev_spec in ev_specs:
            vehicle_catalog_list.append(
                {
                    "vehicle_catalog_id": ev_spec.EV_SPEC_ID,
                    "make": ev_spec.MAKE,
                    "model": ev_spec.MODEL,
                    "year": ev_spec.YEAR,
                    "battery_capacity_kwh": ev_spec.BATTERY_CAPACITY_KWH,
                    "fuel_economy_mpge": kwh_per_km_to_mpge(
                        ev_spec.DISCHARGE_RATE_KWH_PER_KM
                    ),
                    "battery_soc_max": ev_spec.SOC_BOUNDS[1],
                    "max_plug_in_power_kw": ev_spec.CHARGING_POWER_LIMIT_KW,
                    "max_pantograph_power_kw": None,
                }
            )
        self._dict_list_into_low_vol_db(
            vehicle_catalog_list, schema="common", table="vehicle_catalog"
        )

        # In `common.asset` table...
        vehicle_asset_list = []
        for ev in evs_state.values():
            vehicle_asset_list.append(
                {
                    "asset_id": ev.ID,
                    "type": "vehicle",
                    "name": ev.NAME,
                    "description": ev.DESCRIPTION,
                    "parent_id": None,
                    "is_controllable": True,  # ?
                    "device_id": None,
                    "account_id": self.ACCOUNT_ID,
                    "coordinates": None,  # (Not provisioning information, for vehicles.)
                    "is_emulated": True,
                }
            )
        self._dict_list_into_low_vol_db(
            vehicle_asset_list, schema="common", table="asset"
        )

        # In `common.vehicle` table...
        vehicle_list = []
        for ev in evs_state.values():
            vehicle_list.append(
                {
                    "vehicle_id": ev.ID,
                    "charge_point_auth_id": None,
                    "vehicle_catalog_id": ev.EV_SPEC_ID,
                    "battery_efficiency_pc": ev.BATTERY_EFFICIENCY * 100,
                    "vin": None,
                }
            )
        self._dict_list_into_low_vol_db(
            vehicle_list, schema="common", table="vehicle"
        )

    def _provision_charging_sites(
        self, charging_sites_state: Dict[CHARGING_SITE_ID_TYPE, ChargingSite]
    ) -> None:
        # In `common.asset` table...
        charging_site_asset_list = []
        for cs in charging_sites_state.values():
            charging_site_asset_list.append(
                {
                    "asset_id": cs.ID,
                    "type": "charging_site",
                    "name": cs.NAME,
                    "description": cs.DESCRIPTION,
                    "parent_id": None,
                    "is_controllable": False,
                    "device_id": None,
                    "account_id": self.ACCOUNT_ID,
                    "coordinates": cs.to_postgis_point_string(),
                    "is_emulated": True,
                }
            )
        self._dict_list_into_low_vol_db(
            charging_site_asset_list, schema="common", table="asset"
        )

        # In `common.charging_site` table...
        charging_site_list = []
        for cs in charging_sites_state.values():
            charging_site_list.append(
                {
                    "charging_site_id": cs.ID,
                    "address": cs.ADDRESS,
                    "configuration": "{}",  # `JSONB` Postgres type.
                }
            )
        self._dict_list_into_low_vol_db(
            charging_site_list, schema="common", table="charging_site"
        )

    def _provision_charge_points(
        self, flattened_charge_points_state: Dict[CHARGE_POINT_ID_TYPE, ChargePoint]
    ) -> None:
        # In `common.charge_point_catalog` table...
        charging_efficiencies = [
            cp.CHARGING_EFFICIENCY for cp in flattened_charge_points_state.values()
        ]
        assert len(set(charging_efficiencies)) == 1
        dummy_cp_catalog_id = str(uuid())
        dummy_cp_catalog_entry = {
            "charge_point_catalog_id": dummy_cp_catalog_id,
            "make": "dummy-charge_point-make-1",
            "model": "dummy-charge_point-model-1",
            "version": "dummy-charge_point-version-1",
            "charging_efficiency_pc": charging_efficiencies[0] * 100,
            "hardware_charging_rate_limit_unit": "power_kW",
            "accepted_charging_rate_control_unit": "power_kW",
            "charging_mode": "parallel",
            "communication_protocol": None,
        }
        self._dict_list_into_low_vol_db(
            [dummy_cp_catalog_entry], schema="common", table="charge_point_catalog"
        )

        # In `common.asset` table...
        charge_point_asset_list = []
        for cp in flattened_charge_points_state.values():
            charge_point_asset_list.append(
                {
                    "asset_id": cp.ID,
                    "type": "charge_point",
                    "name": cp.NAME,
                    "description": cp.DESCRIPTION,
                    "parent_id": None,
                    "is_controllable": False,
                    "device_id": None,
                    "account_id": self.ACCOUNT_ID,
                    "coordinates": cp.to_postgis_point_string(),
                    "is_emulated": True,
                }
            )
        self._dict_list_into_low_vol_db(
            charge_point_asset_list, schema="common", table="asset"
        )

        # In `common.charge_point` table...
        charge_point_list = []
        for cp in flattened_charge_points_state.values():
            charge_point_list.append(
                {
                    "charge_point_id": cp.ID,
                    "circuit_id": None,
                    "charging_site_id": cp.PARENT_CHARGING_SITE_ID,
                    "charge_point_catalog_id": dummy_cp_catalog_id,
                    "protocol_provided_id": None,
                    "hardware_charging_rate_limit": 999,
                }
            )
        self._dict_list_into_low_vol_db(
            charge_point_list, schema="common", table="charge_point"
        )

    def _provision_connectors(
        self, flattened_connectors_state: Dict[CONNECTOR_ID_TYPE, Connector]
    ) -> None:
        # In `common.connector_catalog` table...
        dummy_connector_catalog_id = str(uuid())
        dummy_connector_catalog_entry = {
            "charge_point_connector_catalog_id": dummy_connector_catalog_id,
            "make": "dummy-connector-make-1",
            "model": "dummy-connector-model-1",
            "version": "dummy-connector-version-1",
            "standard": "dummy-connector-standard-1",
            "type": "cable",
            "hardware_charging_rate_limit_unit": "power_kW",
        }
        self._dict_list_into_low_vol_db(
            [dummy_connector_catalog_entry],
            schema="common",
            table="charge_point_connector_catalog",
        )

        # In `common.asset` table...
        connector_asset_list = []
        for c in flattened_connectors_state.values():
            connector_asset_list.append(
                {
                    "asset_id": c.ID,
                    "type": "charge_point_connector",
                    "name": c.NAME,
                    "description": c.DESCRIPTION,
                    "parent_id": None,
                    "is_controllable": False,
                    "device_id": None,
                    "account_id": self.ACCOUNT_ID,
                    "coordinates": None,
                    "is_emulated": True,
                }
            )
        self._dict_list_into_low_vol_db(
            connector_asset_list, schema="common", table="asset"
        )

        # In `common.charge_point_connector` table...
        connector_list = []
        for c in flattened_connectors_state.values():
            connector_list.append(
                {
                    "charge_point_connector_id": c.ID,
                    "charge_point_connector_catalog_id": dummy_connector_catalog_id,
                    "charge_point_id": c.PARENT_CHARGE_POINT_ID,
                    "charging_site_id": c.PARENT_CHARGING_SITE_ID,
                    "hardware_charging_rate_limit": c.CHARGING_POWER_LIMIT_KW,
                }
            )
        self._dict_list_into_low_vol_db(
            connector_list, schema="common", table="charge_point_connector"
        )

    def _dict_list_into_low_vol_db(
        self, dict_list: List[Dict[str, Any]], schema: str, table: str
    ) -> int:
        return pd.DataFrame(dict_list).to_sql(
            index=False,
            schema=schema,
            name=table,
            if_exists="append",
            con=self.SQLALCHEMY_ENGINE,
        )
