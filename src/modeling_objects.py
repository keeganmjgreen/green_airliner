"""Modeling objects / Python classes used throughout EV Taxis Optimizer and EV Taxis Emulator.

These are 'building blocks' for environment, agent, emulator, etc.

Note: Attributes of a class in CAPITAL LETTERS denote that they are definitely not designed to be
    mutated.
    This convention applies to some stateful classes in other modules as well.

Classes:
- Geographical objects:
  - ``Location``.
  - ``Geofence`` -- uses ``Location``.
  - ``Waypoint`` -- uses ``Location``.
- ``Trip`` and ``TripsDemandForecast`` -- uses ``Location``.
- Assets:
  - ``Asset``.
  - ``EvTaxi`` -- subclass of ``Asset``.
  - Charging site, charge point, and connector -- subclasses of ``Asset``:
    - ``Connector``.
    - ``ChargePoint`` -- also subclass of ``Location``.
    - ``ChargingSite`` -- also subclass of ``Location``.
- ``EnvironmentState``.
  - ``EvAction`` -- used in ``AgentAction``.
- ``AgentAction``.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from copy import deepcopy
from random import shuffle
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import geopandas as gpd
import numpy as np
import shapely

from src.deployment_interfaces import optimizer_dispatch as od
from src.utils.utils import (
    CHARGING_STATUS_CANONICAL_TYPE,
    KWH_PER_MWH,
    cosd,
    datetime_to_utc_string,
    sind,
)

SECONDS_PER_HOUR = 3600

# ID types:
ASSET_ID_TYPE = ID_TYPE = str
EV_ID_TYPE = ASSET_ID_TYPE
CONNECTOR_ID_TYPE = CHARGE_POINT_ID_TYPE = CHARGING_SITE_ID_TYPE = ASSET_ID_TYPE
TRIP_ID_TYPE = ID_TYPE


@dataclasses.dataclass
class IdentifiedObject:
    ID: ID_TYPE

    def __post_init__(self):
        assert type(self.ID) is ID_TYPE


# ==================================================================================================
# Geographical objects

KM_PER_LAT_LON = 111.19492664455873


@dataclasses.dataclass
class Location:
    """A geographic location, with (latitude, longitude) coordinates measured in degrees."""

    X_KM: float
    Y_KM: float
    ALTITUDE_KM: float = 0.0
    TAG: Optional[str] = None

    @classmethod
    def from_shapely_point(cls, point: shapely.geometry.Point) -> Location:
        return cls(LAT=point.y, LON=point.x)

    def to_shapely_point(self) -> shapely.geometry.Point:
        return shapely.geometry.Point(*self.xy_coords)

    @property
    def coords(self) -> np.ndarray:
        return np.array([self.X_KM, self.Y_KM, self.ALTITUDE_KM])

    @property
    def xy_coords(self) -> np.ndarray:
        return np.array([self.X_KM, self.Y_KM])

    @property
    def xyz_coords(self) -> np.ndarray:
        return np.array([self.X_KM, self.Y_KM, self.ALTITUDE_KM])

    @staticmethod
    def direct_distance_km_between(a: Location, b: Location) -> float:
        """Get the direct ('as-the-crow-flies') distance between two coordinate locations."""

        TRUE_LAT_LON = False
        if TRUE_LAT_LON:
            # Distance between true geographic (lat, lon) coordinates:
            # https://www.omnicalculator.com/other/latitude-longitude-distance

            EARTH_RADIUS_KM = 6371
            # TODO: Change when optimizing EV taxis operations on Mars.

            direct_ground_distance_km = (
                2
                * EARTH_RADIUS_KM
                * np.arcsin(
                    np.sqrt(
                        sind((b.LAT - a.LAT) / 2) ** 2
                        + cosd(a.LAT) * cosd(b.LAT) * sind((b.LON - a.LON) / 2) ** 2
                    )
                )
            )
        else:
            # Distance between (lat, lon) coordinates treated as cartesian coordinates:
            direct_ground_distance_km = np.linalg.norm(b.xy_coords - a.xy_coords)

        direct_distance_km = np.sqrt(
            direct_ground_distance_km**2 + (b.ALTITUDE_KM - a.ALTITUDE_KM) ** 2
        )

        return direct_distance_km

    def get_closest_available_asset(self, assets: Dict[ASSET_ID_TYPE, Asset]) -> Asset:
        """
        Also see ``get_first_available_asset``.
        """

        available_assets = [
            asset for asset in assets.values() if asset.has_availability
        ]
        closest_available_asset = available_assets[
            np.argmin(
                [
                    Location.direct_distance_km_between(self, asset.location)
                    for asset in available_assets
                ]
            )
        ]  # TODO: Break ties somehow?

        return closest_available_asset

    def to_json(self) -> Dict[str, Any]:
        """Used by ``EvTaxisEmulatorEnvironment`` via ``Ev.to_json``."""
        return {
            "latitude": self.LAT,
            "longitude": self.LON,
        }

    def to_postgis_point_string(self) -> str:
        return f"POINT({self.LON} {self.LAT})"


@dataclasses.dataclass(repr=False)
class Geofence:
    """One or more closed polygons representing one or more regions on a map, e.g., city limits.

    Used when generating random ``EvTaxi`` locations, when generating random origins and
    destinations of requested trips, and when visualizing regions.
    """

    gseries: gpd.GeoSeries

    @classmethod
    def from_file(cls, filename: Optional[str]) -> Geofence:
        """Create a ``GeoFence`` from a ``.geojson`` file."""

        return cls(gseries=gpd.read_file(filename))

    @classmethod
    def from_lat_lon_bounds(
        cls, lat_bounds: Tuple[float, float], lon_bounds: Tuple[float, float]
    ) -> Geofence:
        """Create a single-polygon, rectangular ``Geofence`` from [min, max] (lat, lon) bounds."""

        min_lat, max_lat = lat_bounds
        min_lon, max_lon = lon_bounds
        return cls.from_lat_lon_list(
            lat_lon_list=[
                (min_lat, min_lon),
                (max_lat, min_lon),
                (max_lat, max_lon),
                (min_lat, max_lon),
            ]
        )

    @classmethod
    def from_lat_lon_list(cls, lat_lon_list: List[Tuple[float, float]]) -> Geofence:
        """Create a single-polygon ``Geofence`` from a list of (lat, lon) coordinates."""

        polygon = shapely.geometry.Polygon(shell=lat_lon_list)
        return cls(
            gseries=gpd.GeoSeries([shapely.geometry.MultiPolygon(polygons=[polygon])])
        )

    def sample_locations(self, n_locations: int) -> Location:
        shapely_obj = self.gseries.sample_points(size=n_locations)[0]
        shapely_points = [shapely_obj] if n_locations == 1 else shapely_obj.geoms
        locations = list(map(Location.from_shapely_point, shapely_points))
        # Randomly sampled Shapely points are sorted by latitude; shuffle them to remove this
        #     non-random aspect:
        shuffle(locations)

        return locations

    def contains(self, location: Location) -> bool:
        return self.gseries.contains(gpd.GeoSeries([location.to_shapely_point()]))[0]

    def bounds(self, axis: Literal["lat", "lon"]) -> Tuple[float, float]:
        xy_axis = {"lat": "x", "lon": "y"}[axis]
        return tuple(self.gseries.bounds[[f"min{xy_axis}", f"max{xy_axis}"]].loc[0])


@dataclasses.dataclass
class Waypoint:
    """A point on a map (with a ``LOCATION``) for a vehicle approaching that location at
    ``DIRECT_APPROACH_SPEED_KMPH``.

    Waypoints are used for trip origins, trip destinations, charging sites, etc.
    """

    LOCATION: Location
    DIRECT_APPROACH_SPEED_KMPH: float
    TIME_INTO_SIMULATION: Union[dt.timedelta, None] = dt.timedelta(0)
    ZERO_ANGLE_OF_ATTACK: bool = False
    # ^ TODO: change to ANGLE_OF_ATTACK: Union[float, None] = None

    # Note: "Direct/directly" = "as the crow flies".

    def get_direct_travel_timedelta(self, origin: Location) -> dt.timedelta:
        direct_distance_km = Location.direct_distance_km_between(origin, self.LOCATION)
        return (
            direct_distance_km / self.DIRECT_APPROACH_SPEED_KMPH * dt.timedelta(hours=1)
        )

    def get_direct_arrival_timestamp(
        self, origin: Location, start_timestamp: dt.datetime
    ) -> dt.datetime:
        """Get direct time of arrival."""

        direct_arrival_timedelta = self.get_direct_travel_timedelta(origin)
        return start_timestamp + direct_arrival_timedelta

    def get_direct_en_route_location(
        self, origin: Location, duration_traveled_so_far: dt.datetime
    ) -> Location:
        """Get the en route location after traveling for a specified duration directly from a given
        origin location to the waypoint's location.

        Note: For (latitude, longitude) coordinates, this is only an approximation.
        """

        en_route_coords = origin.coords + (
            self.LOCATION.coords - origin.coords
        ) * duration_traveled_so_far / self.get_direct_travel_timedelta(origin)

        return Location(*en_route_coords)


# ==================================================================================================
# Trip


@dataclasses.dataclass
class Trip(IdentifiedObject):
    """A trip requested by a taxi customer at the ``REQUESTED_TIMESTAMP`` to go from a pick-up point
    to a drop-off point (the latter of which is known at the ``start_timestamp``).
    """

    REQUESTED_TIMESTAMP: dt.datetime
    ORIGIN: Location  # The pick-up point.
    DESTINATION: Location  # The drop-off point.
    assigned_ev_id: Union[EV_ID_TYPE, None] = None
    start_timestamp: Union[dt.datetime, None] = None
    end_timestamp: Union[dt.datetime, None] = None
    distance_km: Optional[float] = None
    revenue: Optional[float] = None  # Also see `determine_revenue` method.

    @property
    def DIRECT_DISTANCE_KM(self) -> float:
        return Location.direct_distance_km_between(self.ORIGIN, self.DESTINATION)

    @property
    def is_assigned_to_ev(self) -> bool:
        return self.assigned_ev_id is not None

    @property
    def passenger_timedelta(self) -> dt.timedelta:
        """Total travel time for a passenger, from the origin to the destination."""
        if self.start_timestamp is None or self.end_timestamp is None:
            return None
        return self.end_timestamp - self.start_timestamp

    def determine_distance_km(self) -> float:
        """Determine the trip's passenger distance from the origin and destination.

        Also see ``distance_km`` attribute.
        """
        # NOTE: Optionally implement in subclass of ``Trip``.
        return self.DIRECT_DISTANCE_KM

    def determine_revenue(self) -> float:
        """Calculate the revenue from the passenger distance, the passenger timedelta, etc.

        Also see ``revenue`` attribute.
        """
        # NOTE: Implement in subclass of ``Trip``.
        return None

    @classmethod
    def from_dict(cls, _dict: Dict[str, Any]) -> Trip:
        return cls(
            ID=_dict["id"],
            REQUESTED_TIMESTAMP=_dict["requested_timestamp"],
            ORIGIN=Location(
                LAT=_dict["origin_lat"],
                LON=_dict["origin_lon"],
            ),
            DESTINATION=Location(
                LAT=_dict["destination_lat"],
                LON=_dict["destination_lon"],
            ),
            start_timestamp=_dict.get("start_timestamp"),
            end_timestamp=_dict.get("end_timestamp"),
            assigned_ev_id=_dict.get("assigned_ev_id"),
            distance_km=_dict.get("distance_km"),
            revenue=_dict.get("revenue"),
        )

    def to_json(self, current_timestamp: dt.datetime) -> Dict[str, Any]:
        """Used by ``EvTaxisEmulatorEnvironment``.

        The ``EvTaxisEmulator`` calculates ``Trip.start_timestamp`` and ``.end_timestamp`` upon
        EV assignment at the ``.REQUESTED_TIMESTAMP``, but those two fields, along with
        ``.distance_km``, ``.revenue``, and possibly ``.DESTINATION`` would not be known in advance.
        Thus, the ``current_timestamp`` determines whether to report them as None.
        """

        if current_timestamp >= self.start_timestamp:
            pickup_timestamp = datetime_to_utc_string(self.start_timestamp)
        else:
            pickup_timestamp = None

        if current_timestamp >= self.end_timestamp:
            drop_coordinates = self.DESTINATION.to_json()
            drop_timestamp = datetime_to_utc_string(self.end_timestamp)
            duration_secs = self.passenger_timedelta.total_seconds()
            distance_km = self.distance_km
            revenue = self.revenue
        else:
            drop_coordinates = Location(None, None).to_json()
            drop_timestamp = None
            duration_secs = None
            distance_km = None
            revenue = None

        return {
            "id": self.ID,
            "requested_timestamp": datetime_to_utc_string(self.REQUESTED_TIMESTAMP),
            "pickup_coordinates": self.ORIGIN.to_json(),
            "drop_coordinates": drop_coordinates,
            "vehicle_id": self.assigned_ev_id,
            "pickup_timestamp": pickup_timestamp,
            "drop_timestamp": drop_timestamp,
            "duration_secs": duration_secs,
            "distance_km": distance_km,
            "revenue": revenue,
            "driver_id": None,
        }


# ==================================================================================================
# Trips demand forecast


@dataclasses.dataclass
class TripsDemandForecast:
    """A forecast of the number of trips requested, and the corresponding amount of revenue earned,
    for a given spaciotemporal bin (which has both spacial and time components).

    The spacial component of the bin is a given geographic region, whose centerpoint is the
    ``bin_location``.
    The time component of the bin covers a given timespan and is left-aligned; its *start* timestamp
    is the ``forecast_for_timestamp``.

    The forecast is made at the ``event_timestamp``.
    """

    event_timestamp: dt.datetime
    bin_location: Location
    forecast_for_timestamp: dt.datetime
    n_trips_requested: float
    revenue: float


# ==================================================================================================
# Assets


@dataclasses.dataclass(kw_only=True)
class Asset:
    NAME: Optional[str] = None
    DESCRIPTION: Optional[str] = None
    has_availability: bool = dataclasses.field(init=False)
    """Whether the asset is available, or any of its sub-assets are available."""


def get_first_available_asset(assets: Dict[ASSET_ID_TYPE, Asset]) -> Asset:
    """
    Also see ``Location.get_closest_available_asset``.
    """
    available_assets = [asset for asset in assets.values() if asset.has_availability]
    return available_assets[0]


@dataclasses.dataclass(unsafe_hash=True)
class EvSpec:
    """The static specifications (provisioning information) of an EV."""

    DISCHARGE_RATE_KWH_PER_KM: float  # 'Fuel economy'.
    ENERGY_CAPACITY_KWH: float
    CHARGING_POWER_LIMIT_KW: float  # TODO: Change to power levels or connector types?
    SOC_BOUNDS: Tuple[float, float] = (0.0, 1.0)

    EV_SPEC_ID: ID_TYPE = None
    MAKE: Optional[str] = None
    MODEL: Optional[str] = None
    YEAR: Optional[int] = None


@dataclasses.dataclass
class ModelConfig:
    MODEL_SUBPATH: str
    ROTATION_MATRIX: Optional[np.ndarray] = None
    TRANSLATION_VECTOR: Optional[np.ndarray] = None
    LENGTH_M: float = None

    def __post_init__(self):
        if self.ROTATION_MATRIX is None:
            self.ROTATION_MATRIX = np.eye(3)
        if self.TRANSLATION_VECTOR is None:
            self.TRANSLATION_VECTOR = np.zeros(3)


@dataclasses.dataclass(kw_only=True)
class EvTaxi(IdentifiedObject, EvSpec, Asset):
    ID: EV_ID_TYPE
    DEFAULT_SPEED_KMPH: float
    soc: float  # TODO: Change to energy level?
    MODEL_CONFIG: Union[ModelConfig, None] = None
    location: Union[Location, None] = None
    heading: Union[np.ndarray, None] = None
    ENERGY_EFFICIENCY: float = 1.0
    _trip: Union[Trip, None] = None  # Make public?
    waypoints: List[Location] = dataclasses.field(default_factory=(lambda: []))
    connector: Connector = None

    def set_heading(self, to_waypoint: Waypoint) -> np.ndarray:
        heading = to_waypoint.LOCATION.xyz_coords - self.location.xyz_coords
        if to_waypoint.ZERO_ANGLE_OF_ATTACK:
            heading[2] = 0
        self.heading = heading / np.linalg.norm(heading)

    def get_tagged_waypoint(self, location_tag: str) -> Location:
        tagged_waypoints = [
            wp for wp in self.waypoints if wp.LOCATION.TAG == location_tag
        ]
        assert len(tagged_waypoints) == 1
        return tagged_waypoints[0]

    def get_travel_durations_to_tagged_waypoints(self) -> Dict[str, dt.timedelta]:
        current_location = deepcopy(self.location)
        cumulative_travel_duration = dt.timedelta(0)
        travel_durations = {}
        for wp in self.waypoints:
            cumulative_travel_duration += wp.get_direct_travel_timedelta(
                origin=current_location
            )
            current_location = wp.LOCATION
            if wp.LOCATION.TAG is not None:
                travel_durations[wp.LOCATION.TAG] = deepcopy(cumulative_travel_duration)
        return travel_durations

    @property
    def has_availability(self):
        """Whether the EV is not assigned to a trip and not at or en route to a charge point."""
        return (
            self._trip is None
            and not self.is_plugged_in
            and not self.is_en_route_to_charging_site
        )

    @property
    def is_plugged_in(self) -> bool:
        return self.connector is not None

    @property
    def is_charging(self) -> bool:
        return self.is_plugged_in  # TODO: Distinguish between plugged-in and charging.

    def assign_to_trip(self, trip: Union[Trip, None]) -> None:
        if trip is not None:
            # The EV is being assigned to a trip:
            if self._trip is not None:
                raise Exception("EV is already assigned to a trip.")
            self.waypoints.append(
                Waypoint(
                    LOCATION=trip.ORIGIN,
                    DIRECT_APPROACH_SPEED_KMPH=self.DEFAULT_SPEED_KMPH,
                )
            )
            self.waypoints.append(
                Waypoint(
                    LOCATION=trip.DESTINATION,
                    DIRECT_APPROACH_SPEED_KMPH=self.DEFAULT_SPEED_KMPH,
                )
            )
            trip.assigned_ev_id = self.ID
        else:
            if self._trip is None:
                raise Exception("EV is already unassigned.")
            # The EV is being unassigned:
            self._trip.assigned_ev_id = None
        self._trip = trip

    def move_to_location(self, new_location: Location) -> None:
        direct_distance_km = Location.direct_distance_km_between(
            self.location, new_location
        )
        self.charge_with_energy(
            delta_energy_kwh=(-self.DISCHARGE_RATE_KWH_PER_KM * direct_distance_km)
        )

        self.location = new_location

        if isinstance(self.location, ChargingSite):
            # Assign the EV to a connector: the first available one at the first available charge
            #     point at the charging site:
            first_available_cp = get_first_available_asset(
                assets=self.location.charge_points
            )
            first_available_cp_connector = get_first_available_asset(
                assets=first_available_cp.connectors
            )
            # Start charging:
            self.connector = first_available_cp_connector
            self.connector.has_availability = False

    def set_charging_site_waypoint(
        self, charging_site: Union[ChargingSite, None]
    ) -> None:
        if charging_site is not None:
            if self.is_en_route_to_charging_site:
                # Replace the current charging site waypoint:
                self.waypoints[0] = Waypoint(
                    LOCATION=charging_site,
                    DIRECT_APPROACH_SPEED_KMPH=self.DEFAULT_SPEED_KMPH,
                )
            elif not self.is_plugged_in:
                # Set the charging site waypoint:
                self.waypoints.insert(
                    0,
                    Waypoint(
                        LOCATION=charging_site,
                        DIRECT_APPROACH_SPEED_KMPH=self.DEFAULT_SPEED_KMPH,
                    ),
                )
        elif self.is_en_route_to_charging_site:
            # Clear the charging site waypoint:
            self.waypoints = self.waypoints[1:]
        elif self.is_plugged_in:
            # Stop charging:
            self.connector.has_availability = True
            self.connector = None

    @property
    def is_en_route_to_charging_site(self) -> bool:
        return len(self.waypoints) > 0 and isinstance(
            self.waypoints[0].LOCATION, ChargingSite
        )

    def charge_with_energy(
        self, delta_energy_kwh: float, refueling_soc: bool = False
    ) -> None:
        if delta_energy_kwh > 0:
            # If charging:
            delta_energy_kwh *= self.ENERGY_EFFICIENCY
            # Less-than-efficient charging requires extra energy to be delivered; magnitude of delta
            #     SoC will be smaller.
        else:
            # If discharging:
            delta_energy_kwh /= self.ENERGY_EFFICIENCY
            # Less-than-efficient discharging requires extra energy to be spent; magnitude of delta
            #     SoC will be larger.

        if not refueling_soc:
            self.soc += delta_energy_kwh / self.ENERGY_CAPACITY_KWH
        else:
            self.refueling_soc += delta_energy_kwh / self.ENERGY_CAPACITY_KWH

    def charge_for_duration(
        self,
        charging_power_kw: float,
        duration: dt.timedelta,
        refueling_soc: bool = False,
    ) -> None:
        duration_hrs = duration.total_seconds() / SECONDS_PER_HOUR
        self.charge_with_energy(
            delta_energy_kwh=(charging_power_kw * duration_hrs),
            refueling_soc=refueling_soc,
        )

    def to_json(self) -> Dict[str, Any]:
        """Used by ``EvTaxisEmulatorEnvironment``."""
        return {
            "id": self.ID,
            "location": self.location.to_json(),
            "soc_pc": self.soc * 100,
            "charging_status": (
                CHARGING_STATUS_CANONICAL_TYPE["PLUGGED_IN.CHARGING"]
                if self.is_charging
                else CHARGING_STATUS_CANONICAL_TYPE["PLUGGED_IN.NOT_CHARGING"]
                if self.is_plugged_in
                else CHARGING_STATUS_CANONICAL_TYPE["NOT_PLUGGED_IN"]
            ),
            "connector_id": self.connector.ID
            if self.connector is not None
            else None,  # NOTE: Not available from Smartcar.
        }

    @property
    def energy_level_kWh(self) -> float:
        return self.soc * self.ENERGY_CAPACITY_KWH

    def __str__(self) -> str:
        return f"{self.ID}:  SoC = {(self.soc * 100):.2f}%  |  Energy Level = {(self.energy_level_kWh / KWH_PER_MWH):.2f} / {(self.ENERGY_CAPACITY_KWH / KWH_PER_MWH):.2f} MWh"


Airplane = EvTaxi


class Airliner(Airplane):
    pass


@dataclasses.dataclass(kw_only=True)
class Uav(Airplane):
    REFUELING_ENERGY_CAPACITY_KWH: float
    refueling_soc: float  # TODO: Change to refueling energy level?

    @property
    def refueling_energy_level_kWh(self) -> float:
        return self.refueling_soc * self.REFUELING_ENERGY_CAPACITY_KWH

    def __str__(self) -> str:
        return (
            super().__str__()
            + f"  |  Refueling SoC = {(self.refueling_soc * 100):.2f}%  |  Refueling Energy Level = {(self.refueling_energy_level_kWh / KWH_PER_MWH):.2f} / {(self.REFUELING_ENERGY_CAPACITY_KWH / KWH_PER_MWH):.2f} MWh"
        )


# --------------------------------------------------------------------------------------------------
# Charging site, charge point, and connector


@dataclasses.dataclass(kw_only=True)
class Connector(IdentifiedObject, Asset):
    """A charging connector of a charge point."""

    ID: CONNECTOR_ID_TYPE
    CHARGING_POWER_LIMIT_KW: float
    # CONNECTOR_TYPE
    PARENT_CHARGE_POINT_ID: CHARGE_POINT_ID_TYPE
    PARENT_CHARGE_POINT_LOCATION: Location
    PARENT_CHARGING_SITE_ID: CHARGING_SITE_ID_TYPE
    has_availability: bool = True
    # TODO: ^ Remove default? (Same goes for `ChargePoint` and `ChargingSite`.)


@dataclasses.dataclass(kw_only=True)
class ChargePoint(IdentifiedObject, Asset, Location):
    ID: CHARGE_POINT_ID_TYPE
    connectors: Dict[CONNECTOR_ID_TYPE, Connector]
    PARENT_CHARGING_SITE_ID: CHARGING_SITE_ID_TYPE
    CHARGING_EFFICIENCY: float = 1.0  # NOTE: Unused.
    is_open: bool = True

    @property
    def has_availability(self):
        return (
            any(c.has_availability for c in self.connectors.values()) and self.is_open
        )

    def to_json(self) -> Dict[str, Any]:
        """Used by ``EvTaxisEmulatorEnvironment``."""
        return {
            "id": self.ID,
            "connectors": [
                {
                    "id": connector.ID,
                    "is_plugged_in": not connector.has_availability,
                }
                for connector in self.connectors.values()
            ],
            "is_open": self.is_open,
        }


@dataclasses.dataclass(kw_only=True)
class ChargingSite(IdentifiedObject, Asset, Location):
    ID: CHARGING_SITE_ID_TYPE
    charge_points: Dict[CHARGE_POINT_ID_TYPE, ChargePoint]
    ADDRESS: Optional[str] = None
    is_open: bool = True

    @property
    def has_availability(self):
        return (
            any(cp.has_availability for cp in self.charge_points.values())
            and self.is_open
        )

    @property
    def location(self):
        return Location(LAT=self.LAT, LON=self.LON)


# ==================================================================================================


TRIPS_DEMAND_FORECASTS_TYPE = Dict[dt.datetime, List[TripsDemandForecast]]


@dataclasses.dataclass
class EnvironmentState:
    """The state of assets (EV taxis, charge points) and ongoing trips, as well as the trips demand
    forecasts, which the agent of the EV Taxis Optimizer can use to make a decision.

    Includes those assets' provisioning information, in case it changes between EV Taxis Optimizer
    iterations.

    The ``ongoing_trips_state`` and ``trips_demand_forecasts`` attributes are Optional, but should
    only be set to None when instantiating as the `START_STATE` of the ``EvTaxisEmulator``, from
    which the emulator should populate them upon updating its EnvironmentState.

    See attributes' docstrings (e.g., that of the ``EvTaxi`` class) for details.

    Note: Despite what the name implies, the environment itself is not stateful; the
    ``EvTaxisEmulator`` or ``EvTaxisEmulator`` is.
    """

    evs_state: Dict[EV_ID_TYPE, EvTaxi]


@dataclasses.dataclass
class EvAction:
    waypoint_charging_site_id: Union[CHARGING_SITE_ID_TYPE, None]
    # ^ Not a `Waypoint`; the charging site's location will be set as the EV's (only) waypoint.


@dataclasses.dataclass
class AgentAction:
    ev_actions: Dict[EV_ID_TYPE, EvAction]

    def to_asset_actions(self) -> List[od.AssetAction]:
        """
        Used by the deployed EV Taxis Optimizer component.
        """
        return [
            od.AssetAction(
                assetType="vehicle",
                assetId=ev_id,
                priority=None,
                recommendedCommands=[
                    od.ChargingSiteRecommendation(
                        chargingSiteId=ev_action.waypoint_charging_site_id
                    )
                ],
            )
            for ev_id, ev_action in self.ev_actions.items()
        ]

    @classmethod
    def from_asset_actions(cls, asset_actions: List[od.AssetAction]) -> AgentAction:
        """
        Used by the deployed EV Taxis Emulator component.
        """
        ev_actions = {}
        for asset_action in asset_actions:
            assert asset_action.contains_recommended_command_type(
                od.ChargingSiteRecommendation
            )
            if asset_action.contains_recommended_command_type(
                od.ChargingSiteRecommendation
            ):
                assert asset_action.assetType == "vehicle"
                recommended_command = asset_action.get_1x_recommended_command_type(
                    od.ChargingSiteRecommendation
                )
                ev_actions[asset_action.assetId] = EvAction(
                    waypoint_charging_site_id=recommended_command.chargingSiteId
                )
        return cls(ev_actions)
