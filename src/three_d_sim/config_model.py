from __future__ import annotations

import datetime as dt

import json
from pathlib import Path
from typing import Any, Dict, List, Literal, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


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


class SimulationConfig(Model):
    airliner_config: Dict[str, Any]
    airliner_flight_path_config: Dict[str, Any]
    n_uavs_per_flyover_airport: Dict[str, Dict[str, int]] = Field(
        title="Number of UAVs per Flyover Airport"
    )
    uavs_config: Dict[str, Any] = Field(title="UAVs Config")
    uavs_flight_path_config: Dict[str, Any] = Field(title="UAVs Flight Path Config")
    ratepoints: List[Ratepoint]
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
