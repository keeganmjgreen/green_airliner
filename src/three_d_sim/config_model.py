from __future__ import annotations

import datetime as dt

from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, Union
from pydantic import BaseModel

import yaml


class Timepoint(BaseModel):
    elapsed_minutes: Union[float, str]
    elapsed_time: Union[dt.timedelta, None] = None

    def set_elapsed_time(self, reference_times: Dict[str, int]) -> dt.timedelta:
        self.elapsed_time = dt.timedelta(
            minutes=eval(str(self.elapsed_minutes), reference_times)
        )

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


class UavsZoompointsConfig(BaseModel):
    to_airport: List[Zoompoint]
    from_airport: List[Zoompoint]


class ZoompointsConfig(BaseModel):
    airliner_zoompoints: List[Zoompoint]
    uavs_zoompoints_config: UavsZoompointsConfig


class MapViewConfig(BaseModel):
    map_texture_fpath: str
    models_scale_factor: float
    zoom: float


class VizConfig(BaseModel):
    min_frame_duration_s: float
    scene_w: int
    scene_h: int
    theme: Literal["day", "night"]
    zoompoints_config: ZoompointsConfig
    landed_uavs_waiting_time_mins: float
    map_texture_fpath: str
    map_view_config: MapViewConfig

    @property
    def scene_size(self) -> Tuple[int, int]:
        return self.scene_w, self.scene_h


class SimulationConfig(BaseModel):
    airliner_config: Dict[str, Any]
    airliner_flight_path_config: Dict[str, Any]
    n_uavs_per_flyover_airport: Dict[str, Dict[str, int]]
    uavs_config: Dict[str, Any]
    uavs_flight_path_config: Dict[str, Any]
    ratepoints: List[Ratepoint]
    viz_config: VizConfig

    @classmethod
    def from_yaml(
        cls, dir: Union[Path, str], fname: str = "simulation_config.yml"
    ) -> SimulationConfig:
        return cls(**yaml.safe_load(Path(dir, fname).read_text()))
