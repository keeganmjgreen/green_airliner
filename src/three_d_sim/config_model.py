from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import yaml


class Ratepoint:
    elapsed_minutes: Union[float, str]
    rate: float


class Zoompoint:
    elapsed_minutes: Union[float, str]
    zoom: float


class UavsZoompointsConfig:
    to_airport: List[Zoompoint]
    from_airport: List[Zoompoint]


class ZoompointsConfig:
    airliner_zoompoints: List[Zoompoint]
    uavs_zoompoints_config: UavsZoompointsConfig


class MapViewConfig:
    models_scale_factor: float
    zoom: float


class VizConfig:
    min_frame_duration_s: float
    scene_w: int
    scene_h: int
    zoompoints_config: ZoompointsConfig
    landed_uavs_waiting_time_mins: float
    map_view_config: MapViewConfig

    @property
    def scene_size(self) -> Tuple[int, int]:
        return self.scene_w, self.scene_h


class SimulationConfig:
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
        return yaml.safe_load(Path(dir, fname).read_text())
