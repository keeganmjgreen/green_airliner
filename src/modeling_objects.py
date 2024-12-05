from __future__ import annotations

import dataclasses
import datetime as dt
from copy import deepcopy
from typing import Literal, Optional, Type

import numpy as np
import pandas as pd

from src.feasibility_study.modeling_objects import BaseAirliner as AirlinerSpec
from src.feasibility_study.modeling_objects import BaseAirplane as AirplaneSpec
from src.feasibility_study.modeling_objects import Fuel
from src.feasibility_study.modeling_objects import Uav as UavSpec
from src.three_d_sim.viz_models import ModelConfig
from src.utils.utils import (
    M_PER_KM,
    MJ_PER_KWH,
    SECONDS_PER_HOUR,
    cosd,
    sind,
    timedelta_to_minutes,
)
from three_d_sim.simulation_config_schema import (
    AirlinerConfig,
    AirlinerFlightPathConfig,
)

# ==================================================================================================
# Geographical objects

KM_PER_LAT_LON = 111.19492664455873
AIRPORT_LOCATIONS_CSV_PATH = "src/three_d_sim/airport_locations.csv"
AirportCode = str
ServiceSide = Literal["to-airport", "from-airport"]


@dataclasses.dataclass
class Location:
    """A geographic location, with (latitude, longitude) coordinates measured in degrees."""

    X_KM: float
    Y_KM: float
    ALTITUDE_KM: float = 0.0
    TAG: Optional[str] = None

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


@dataclasses.dataclass(kw_only=True)
class AirportLocation(Location):
    CODE: AirportCode


def get_all_airport_locations(
    normalize_coords: bool = False,
) -> dict[AirportCode, AirportLocation]:
    DEFAULT_ALTITUDE = 0.0

    airport_location_df = pd.read_csv(AIRPORT_LOCATIONS_CSV_PATH)
    all_airport_locations = {
        row["airport_code"]: AirportLocation(
            Y_KM=(row["lat"] * KM_PER_LAT_LON),
            X_KM=(row["lon"] * KM_PER_LAT_LON),
            ALTITUDE_KM=row.get("altitude", DEFAULT_ALTITUDE),
            CODE=row["airport_code"],
        )
        for row in airport_location_df.to_dict("records")
    }
    if normalize_coords:
        min_y_km, max_y_km = [
            m(loc.Y_KM for loc in all_airport_locations.values()) for m in [min, max]
        ]
        min_x_km, max_x_km = [
            m(loc.X_KM for loc in all_airport_locations.values()) for m in [min, max]
        ]
        for loc in all_airport_locations.values():
            loc.Y_KM = loc.Y_KM - (min_y_km + max_y_km) / 2
            loc.X_KM = loc.X_KM - (min_x_km + max_x_km) / 2
    return all_airport_locations


ALL_AIRPORT_LOCATIONS = get_all_airport_locations(normalize_coords=True)


@dataclasses.dataclass
class Waypoint:
    """A point on a map (with a ``LOCATION``) for a vehicle approaching that location at
    ``DIRECT_APPROACH_SPEED_KMPH``.

    Waypoints are used for trip origins, trip destinations, charging sites, etc.
    """

    LOCATION: Location
    DIRECT_APPROACH_SPEED_KMPH: float | None = None
    TIME_INTO_SIMULATION: dt.timedelta | None = dt.timedelta(0)
    ZERO_ANGLE_OF_ATTACK: bool = False
    # ^ TODO: change to ANGLE_OF_ATTACK: float | None = None

    # Note: "Direct/directly" = "as the crow flies".

    def get_direct_travel_timedelta(self, origin: Location) -> dt.timedelta:
        direct_distance_km = Location.direct_distance_km_between(origin, self.LOCATION)
        return (
            direct_distance_km / self.DIRECT_APPROACH_SPEED_KMPH * dt.timedelta(hours=1)
        )

    def get_direct_arrival_time(
        self, origin: Location, start_time: dt.timedelta
    ) -> dt.timedelta:
        """Get direct time of arrival."""

        direct_arrival_timedelta = self.get_direct_travel_timedelta(origin)
        return start_time + direct_arrival_timedelta

    def get_direct_en_route_location(
        self, origin: Location, duration_traveled_so_far: dt.timedelta
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
# Flight paths


@dataclasses.dataclass
class FlightPath:
    takeoff_speed_kmph: float
    takeoff_distance_km: float
    takeoff_leveling_distance_km: float
    rate_of_climb_mps: float
    climb_leveling_distance_km: float
    cruise_altitude_km: float
    cruise_speed_kmph: float
    turning_radius_km: float
    descent_leveling_distance_km: float
    rate_of_descent_mps: float
    landing_leveling_distance_km: float
    landing_distance_km: float
    landing_speed_kmph: float

    def __post_init__(self):
        assert self.takeoff_leveling_distance_km < self.takeoff_distance_km
        assert self.landing_leveling_distance_km < self.landing_distance_km

    @property
    def rate_of_climb_kmph(self) -> float:
        return self.rate_of_climb_mps / M_PER_KM * SECONDS_PER_HOUR

    @property
    def rate_of_descent_kmph(self) -> float:
        return self.rate_of_descent_mps / M_PER_KM * SECONDS_PER_HOUR


@dataclasses.dataclass(kw_only=True)
class AirlinerFlightPath(FlightPath):
    origin_airport: AirportLocation | AirportCode
    flyover_airports: list[AirportLocation | AirportCode]
    destination_airport: AirportLocation | AirportCode
    speed_change_distance_km: float

    def __post_init__(self):
        self.origin_airport = ALL_AIRPORT_LOCATIONS[self.origin_airport]
        self.flyover_airports = [
            ALL_AIRPORT_LOCATIONS[a] for a in self.flyover_airports
        ]
        self.destination_airport = ALL_AIRPORT_LOCATIONS[self.destination_airport]

    @classmethod
    def from_configs(
        cls,
        airliner_fp_config: AirlinerFlightPathConfig,
        airliner_config: AirlinerConfig,
    ) -> AirlinerFlightPath:
        return cls(
            origin_airport=airliner_fp_config.origin_airport_code,
            flyover_airports=airliner_fp_config.flyover_airport_codes,
            destination_airport=airliner_fp_config.destination_airport_code,
            takeoff_speed_kmph=airliner_fp_config.takeoff_speed_kmph,
            takeoff_distance_km=airliner_fp_config.takeoff_distance_km,
            takeoff_leveling_distance_km=airliner_fp_config.takeoff_leveling_distance_km,
            rate_of_climb_mps=airliner_fp_config.rate_of_climb_mps,
            climb_leveling_distance_km=airliner_fp_config.climb_leveling_distance_km,
            cruise_altitude_km=airliner_fp_config.cruise_altitude_km,
            cruise_speed_kmph=airliner_config.airplane_spec.cruise_speed_kmph,
            speed_change_distance_km=airliner_fp_config.speed_change_distance_km,
            turning_radius_km=airliner_fp_config.turning_radius_km,
            descent_leveling_distance_km=airliner_fp_config.descent_leveling_distance_km,
            rate_of_descent_mps=airliner_fp_config.rate_of_descent_mps,
            landing_leveling_distance_km=airliner_fp_config.landing_leveling_distance_km,
            landing_distance_km=airliner_fp_config.landing_distance_km,
            landing_speed_kmph=airliner_fp_config.landing_speed_kmph,
        )

    @property
    def flyover_airport_codes(self) -> list[AirportCode]:
        return [a.CODE for a in self.flyover_airports]

    @property
    def airports(self) -> list[AirportLocation]:
        return (
            [self.origin_airport] + self.flyover_airports + [self.destination_airport]
        )


@dataclasses.dataclass(kw_only=True)
class UavFlightPath(FlightPath):
    home_airport: AirportLocation | AirportCode
    arc_radius_km: float
    refueling_altitude_km: float
    refueling_distance_km: float
    service_side: Literal["to_airport", "from_airport"] | None = None
    undocking_distance_from_airport_km: float | None = None
    airliner_clearance_speed_kmph: float | None = None
    airliner_clearance_distance_km: float | None = None
    airliner_clearance_altitude_km: float | None = None

    def __post_init__(self):
        self.home_airport = ALL_AIRPORT_LOCATIONS[self.home_airport]

    @property
    def AVG_AIRLINER_CLEARANCE_SPEED_KMPH(self) -> float | None:
        if self.airliner_clearance_speed_kmph is not None:
            return (self.cruise_speed_kmph + self.airliner_clearance_speed_kmph) / 2
        else:
            return None


# ==================================================================================================
# Airplanes


AirplaneId = str
UavId = AirplaneId


@dataclasses.dataclass(kw_only=True)
class Airplane:
    id: AirplaneId
    airplane_spec: Type[AirplaneSpec]
    refueling_rate_kW: float
    initial_energy_level_pc: float
    energy_level_pc_bounds: tuple[float, float] = (0.0, 100.0)
    energy_efficiency_pc: float = 100.0
    flight_path: FlightPath | None = None
    viz_model: ModelConfig | None = None

    energy_capacity_MJ: float = dataclasses.field(init=False)
    energy_consumption_rate_MJ_per_km: float = dataclasses.field(init=False)
    energy_level_pc: float = dataclasses.field(init=False)
    location: Location | None = dataclasses.field(init=False)
    heading: np.ndarray | None = dataclasses.field(init=False)
    waypoints: list[Waypoint] = dataclasses.field(init=False)

    def __post_init__(self):
        self.energy_capacity_MJ = self.airplane_spec.energy_capacity_MJ
        self.energy_consumption_rate_MJ_per_km = self.airplane_spec.energy_consumption_rate_MJ_per_km
        self.energy_level_pc = deepcopy(self.initial_energy_level_pc)
        self.location = None
        self.heading = None
        self.waypoints = []

    @property
    def all_locations(self) -> list[Location]:
        return [
            loc.xyz_coords
            for loc in [self.location] + [wp.LOCATION for wp in self.waypoints]
        ]

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

    @property
    def all_tagged_waypoints(self) -> list[Location]:
        return [wp.LOCATION for wp in self.waypoints if wp.LOCATION.TAG is not None]

    def get_travel_durations_to_tagged_waypoints(self) -> dict[str, dt.timedelta]:
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

    def get_elapsed_time_at_tagged_waypoints(self) -> dict[str, dt.timedelta]:
        return {
            k: self.waypoints[0].TIME_INTO_SIMULATION + v
            for k, v in self.get_travel_durations_to_tagged_waypoints().items()
        }

    def get_elapsed_time_at_tagged_waypoints_ser(self, decimals: int = 1) -> pd.Series:
        ser = (
            pd.Series(self.get_elapsed_time_at_tagged_waypoints()).apply(
                timedelta_to_minutes
            )
        ).rename("minutes")
        ser = ser.round(decimals)
        if decimals == 0:
            ser = ser.astype(int)
        return ser

    def move_to_location(self, new_location: Location) -> None:
        direct_distance_km = Location.direct_distance_km_between(
            self.location, new_location
        )
        self.charge_with_energy(
            delta_energy_MJ=(-self.energy_consumption_rate_MJ_per_km * direct_distance_km)
        )

        self.location = new_location

    def charge_with_energy(
        self, delta_energy_MJ: float, refueling_energy_level: bool = False
    ) -> None:
        if delta_energy_MJ > 0:
            # If charging:
            delta_energy_MJ *= self.energy_efficiency_pc / 100
            # Less-than-efficient charging requires extra energy to be delivered; magnitude of delta
            #     SoC will be smaller.
        else:
            # If discharging:
            delta_energy_MJ /= self.energy_efficiency_pc / 100
            # Less-than-efficient discharging requires extra energy to be spent; magnitude of delta
            #     SoC will be larger.

        if not refueling_energy_level:
            self.energy_level_pc += delta_energy_MJ / self.energy_capacity_MJ * 100
            self.energy_level_pc = np.clip(a=self.energy_level_pc, a_min=None, a_max=self.energy_level_pc_bounds[1])
        else:
            self.refueling_energy_level_pc += delta_energy_MJ / self.refueling_energy_capacity_MJ * 100

    def charge_for_duration(
        self,
        charging_power_kw: float,
        duration: dt.timedelta,
        refueling_energy_level: bool = False,
    ) -> None:
        duration_h = duration / dt.timedelta(hours=1)
        self.charge_with_energy(
            delta_energy_MJ=(charging_power_kw * duration_h * MJ_PER_KWH),
            refueling_energy_level=refueling_energy_level,
        )

    @property
    def energy_level_MJ(self) -> float:
        return self.energy_level_pc / 100 * self.energy_capacity_MJ

    def __str__(self) -> str:
        return f"{self.id}:  SoC = {(self.energy_level_pc):.2f}%  |  Energy Level = {self.energy_level_MJ:.2f} / {self.energy_capacity_MJ:.2f} MJ"


@dataclasses.dataclass(kw_only=True)
class Airliner(Airplane):
    id: str = "Airliner"
    airplane_spec: Type[AirlinerSpec]
    docked_uav: AirplaneId | None = None


@dataclasses.dataclass(kw_only=True)
class Uav(Airplane):
    id: UavId
    airplane_spec: Type[UavSpec]
    payload_fuel: Fuel
    initial_refueling_energy_level_pc: float

    refueling_energy_capacity_MJ: float = dataclasses.field(init=False)
    refueling_energy_level_pc: float = dataclasses.field(init=False)

    def __post_init__(self):
        self.refueling_energy_capacity_MJ = self.airplane_spec.refueling_energy_capacity_MJ(self.payload_fuel)
        self.refueling_energy_level_pc = deepcopy(self.initial_refueling_energy_level_pc)

        super().__post_init__()

    @property
    def refueling_energy_level_MJ(self) -> float:
        return self.refueling_energy_level_pc / 100 * self.refueling_energy_capacity_MJ

    def __str__(self) -> str:
        return (
            super().__str__()
            + f"  |  Refueling SoC = {self.refueling_energy_level_pc:.2f}%  |  Refueling Energy Level = {self.refueling_energy_level_MJ:.2f} / {self.refueling_energy_capacity_MJ:.2f} MJ"
        )


# ==================================================================================================


@dataclasses.dataclass
class AirplanesState:
    """The state of the airplanes."""

    airplanes: dict[AirplaneId, Airplane]
