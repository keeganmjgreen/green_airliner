from __future__ import annotations

import dataclasses
import datetime as dt
from copy import deepcopy
from typing import Dict, List, Optional, Tuple, Type, Union

import numpy as np
import pandas as pd

from src.feasibility_study.modeling_objects import BaseAirliner as AirlinerSpec
from src.feasibility_study.modeling_objects import BaseAirplane as AirplaneSpec
from src.feasibility_study.modeling_objects import Fuel
from src.feasibility_study.modeling_objects import Uav as UavSpec
from src.specs import airliner_lookup, uav_lookup
from src.three_d_sim.viz_models import (
    ModelConfig,
    airliner_model_lookup,
    uav_model_lookup,
)
from src.utils.utils import MJ_PER_KWH, cosd, sind, timedelta_to_minutes

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
# Airplanes


AirplaneId = str


@dataclasses.dataclass(kw_only=True)
class Airplane:
    id: AirplaneId
    airplane_spec: Union[Type[AirplaneSpec], str]
    refueling_rate_kW: float
    initial_energy_level_pc: float
    energy_level_pc_bounds: Tuple[float, float] = (0.0, 100.0)
    energy_efficiency_pc: float = 100.0
    viz_model: Union[ModelConfig, str, None] = None

    energy_capacity_MJ: float = dataclasses.field(init=False)
    energy_consumption_rate_MJ_per_km: float = dataclasses.field(init=False)
    energy_level_pc: float = dataclasses.field(init=False)
    location: Union[Location, None] = dataclasses.field(init=False)
    heading: Union[np.ndarray, None] = dataclasses.field(init=False)
    waypoints: List[Location] = dataclasses.field(init=False)

    def __post_init__(self):
        self.energy_capacity_MJ = self.airplane_spec.energy_capacity_MJ
        self.energy_consumption_rate_MJ_per_km = self.airplane_spec.energy_consumption_rate_MJ_per_km
        self.energy_level_pc = deepcopy(self.initial_energy_level_pc)
        self.location = None
        self.heading = None
        self.waypoints = []

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

    def get_elapsed_time_at_tagged_waypoints(self) -> Dict[str, dt.timedelta]:
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
    airplane_spec: Union[Type[AirlinerSpec], str]
    docked_uav: Union[AirplaneId, None] = None

    def __post_init__(self):
        if not isinstance(self.airplane_spec, AirlinerSpec):
            self.airplane_spec = airliner_lookup[self.airplane_spec.name]

        if type(self.viz_model) is not ModelConfig:
            self.viz_model = airliner_model_lookup[self.viz_model.name]

        super().__post_init__()


@dataclasses.dataclass(kw_only=True)
class Uav(Airplane):
    airplane_spec: Union[Type[UavSpec], str]
    payload_fuel: Fuel
    initial_refueling_energy_level_pc: float

    refueling_energy_capacity_MJ: float = dataclasses.field(init=False)
    refueling_energy_level_pc: float = dataclasses.field(init=False)

    def __post_init__(self):
        if not isinstance(self.airplane_spec, UavSpec):
            self.airplane_spec = uav_lookup[self.airplane_spec]

        if type(self.viz_model) is not ModelConfig:
            self.viz_model = uav_model_lookup[self.viz_model.name]

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

    airplanes: Dict[AirplaneId, Airplane]
