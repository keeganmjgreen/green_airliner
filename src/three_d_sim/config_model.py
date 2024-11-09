from __future__ import annotations

import datetime as dt

import json
from pathlib import Path
from typing import Dict, List, Literal, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field

AIRPORT_CODE_TYPE = str


class Model(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


class AirlinerConfig(Model):
    """Configuration of the airliner."""
    airplane_spec: str
    refueling_rate_kW: float
    initial_energy_level_pc: float
    viz_model: str


class FlightPathConfig(Model):
    takeoff_speed_kmph: float
    takeoff_distance_km: float
    takeoff_leveling_distance_km: float
    rate_of_climb_mps: float
    climb_leveling_distance_km: float
    descent_leveling_distance_km: float
    rate_of_descent_mps: float
    landing_leveling_distance_km: float
    landing_distance_km: float
    landing_speed_kmph: float


class AirlinerFlightPathConfig(FlightPathConfig):
    """Configuration of the airliner's flight path."""
    origin_airport: AIRPORT_CODE_TYPE
    flyover_airports: List[AIRPORT_CODE_TYPE]
    destination_airport: AIRPORT_CODE_TYPE
    cruise_altitude_km: float
    turning_radius_km: float
    speed_change_distance_km: float


class UavsFlightPathConfig(FlightPathConfig):
    """Configuration of the UAVs' flight paths (all of which are assumed to follow the same
    parameters).
    """
    takeoff_speed_kmph: float
    takeoff_distance_km: float
    takeoff_leveling_distance_km: float
    rate_of_climb_mps: float
    climb_leveling_distance_km: float
    default_cruise_altitude_km: float
    arc_radius_km: float
    airliner_uav_docking_distance_km: float
    smallest_undocking_distance_from_airport_km: float
    inter_uav_clearance_km: float
    airliner_clearance_speed_kmph: float
    airliner_clearance_distance_km: float
    default_airliner_clearance_altitude_km: float
    inter_uav_vertical_dist_km: float


class NUavsAtFlyOverAirport(Model):
    to_airport: int
    from_airport: int


class UavsConfig(Model):
    """Configuration of the UAVs (all of which are assumed to be the same)."""
    airplane_spec: str
    refueling_rate_kW: float
    initial_energy_level_pc: float
    initial_refueling_energy_level_pc: float
    viz_model: str


class Timepoint(Model):
    elapsed_mins: Union[float, str]

    def evaluate_elapsed_mins(self, reference_times: Dict[str, int]) -> dt.timedelta:
        self.elapsed_mins = eval(str(self.elapsed_mins), reference_times)

    @property
    def value(self) -> float:
        raise NotImplementedError


class Ratepoint(Timepoint):
    rate: float

    @property
    def value(self) -> float:
        return self.rate


class Zoompoint(Timepoint):
    zoom: float

    @property
    def value(self) -> float:
        return self.zoom


class UavsZoompointsConfig(Model):
    to_airport: List[Zoompoint]
    from_airport: List[Zoompoint]


class ZoompointsConfig(Model):
    airliner_zoompoints: List[Zoompoint]
    uavs_zoompoints_config: UavsZoompointsConfig


class MapViewConfig(Model):
    map_texture_fpath: str
    models_scale_factor: float
    zoom: float


class VizConfig(Model):
    """Configuration to use when visualizing the airliner and UAVs while the simulation runs."""
    max_frame_rate_fps: int
    """Maximum frame rate (in frames per second) at which to render the visualization. If updating a
    frame takes too long, the actual frame rate will be less.
    """
    scene_w: int
    """Width (in pixels) of the viewport in which the visualization is rendered."""
    scene_h: int
    """Height (in pixels) of the viewport in which the visualization is rendered."""
    theme: Literal["day", "night"]
    """Color theme to use for the sky and (if no `map_texture_fpath` is specified) the ground."""
    zoompoints_config: ZoompointsConfig
    landed_uavs_waiting_time_mins: float
    """When tracking a UAV, how long (in minutes) to wait after a flyover airport's last UAV lands
    before ending that UAV's visualization () 
    """
    map_texture_fpath: str
    map_view_config: MapViewConfig

    @property
    def scene_size(self) -> Tuple[int, int]:
        return self.scene_w, self.scene_h


class SimulationConfig(Model):
    """Configuration for the mid-air refueling simulation."""
    airliner_config: AirlinerConfig
    airliner_flight_path_config: AirlinerFlightPathConfig
    n_uavs_per_flyover_airport: Dict[AIRPORT_CODE_TYPE, NUavsAtFlyOverAirport]
    """Number of UAVs at each flyover airport."""
    uavs_config: UavsConfig
    uavs_flight_path_config: UavsFlightPathConfig
    ratepoints: List[Ratepoint]
    viz: bool = True
    viz_config: VizConfig = Field(title="Vizualization Config")

    @classmethod
    def from_yaml(
        cls, dir: Union[Path, str], fname: str = "simulation_config.yml"
    ) -> SimulationConfig:
        return cls(**yaml.safe_load(Path(dir, fname).read_text()))


if __name__ == "__main__":
    simulation_config_schema = SimulationConfig.model_json_schema()
    json.dump(
        simulation_config_schema,
        Path("../configs/simulation_config_json_schema.json").open("w"),
        indent=4,
    )
