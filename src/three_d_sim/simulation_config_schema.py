from __future__ import annotations

import datetime as dt
import json
from enum import Enum
from pathlib import Path
from typing import Literal, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.feasibility_study.modeling_objects import BaseAirliner as AirlinerSpec
from src.feasibility_study.modeling_objects import Uav as UavSpec
from src.specs import airliner_lookup, uav_lookup
from src.three_d_sim.viz_models import (
    ModelConfig,
    airliner_model_lookup,
    uav_model_lookup,
)

AirportCode = str


class Model(BaseModel):
    model_config = ConfigDict(use_attribute_docstrings=True)


AirlinerSpecName = Enum("AirlinerSpecName", {k: k for k in airliner_lookup.keys()})
AirlinerVizModelName = Enum(
    "AirlinerVizModelName", {k: k for k in airliner_model_lookup.keys()}
)


class AirlinerConfig(Model):
    """Configuration of the airliner."""

    airplane_spec_name: AirlinerSpecName = Field(title="Airplane Spec Name")
    """Which airplane spec to use for the airliner. Must be one of those listed below. `specs.py` \
    acts as a registry for these and, if a different airliner is desired, a new spec can be added \
    there.
    """
    refueling_rate_kW: float = Field(title="Refueling Rate (kW)")
    """The maximum rate (in kilowatts / joules per second) at which the airliner can be refueled \
    (by a UAV). Can represent refueling at a rate of `x` joules of fuel per second, or recharging \
    at a rate of `x` kilowatts of electricity.
    """
    initial_energy_level_pc: float = Field(title="Initial Energy Level (%)")
    """The amount of energy (alternately, the corresponding amount of fuel) that the airliner \
    starts with before takeoff from its origin airport. Expressed as a percentage (0-100) of the \
    airliner's energy capacity.
    """
    viz_model_name: AirlinerVizModelName = Field(title="Viz Model Name")
    """Which 3D model to use for the airliner, when `viz_enabled` is set to true. Must be one of \
    those listed below. `viz_models.py` acts as a registry for these and, if a different 3D model \
    is desired, a new one can be added there.
    """

    @property
    def airplane_spec(self) -> AirlinerSpec:
        return airliner_lookup[self.airplane_spec_name.name]

    @property
    def viz_model(self) -> ModelConfig:
        return airliner_model_lookup[self.viz_model_name.name]


class FlightPathConfig(Model):
    takeoff_speed_kmph: float = Field(title="Takeoff Speed (km/h)")
    """The speed (in kilometers per hour) required for the airplane to take off."""
    takeoff_distance_km: float = Field(title="Takeoff Distance (km)")
    """The distance (in kilometers) for the airplane to accelerate from a standstill until \
    reaching the takeoff speed.
    """
    takeoff_leveling_distance_km: float = Field(title="Takeoff Leveling Distance (km)")
    """See "Flight path configuration" diagram."""
    rate_of_climb_mps: float = Field(title="Rate of Climb (m/s)")
    """The speed (in meters per second) at which the airliner climbs between takeoff and cruise. \
    This is only the vertical component of the aiplane's velocity.
    """
    climb_leveling_distance_km: float = Field(title="Climb Leveling Distance (km)")
    """See "Flight path configuration" diagram. Affects how long the airplane takes of level off \
    between climb and cruise.
    """
    descent_leveling_distance_km: float = Field(title="")
    """See "Flight path configuration" diagram."""
    rate_of_descent_mps: float = Field(title="Rate of Descent (m/s)")
    """The speed (in meters per second) at which the airliner descends between cruise and landing. \
    This is only the vertical component of the airplane's velocity.
    """
    landing_leveling_distance_km: float = Field(title="Landing Leveling Distance (km)")
    """See "Flight path configuration" diagram. Affects how long the airplane takes to land."""
    landing_distance_km: float = Field(title="Landing Distance (km)")
    """The distance (in kilometers) for the airplane to decelerate from landing speed to a \
    standstill.
    """
    landing_speed_kmph: float = Field(title="Landing Speed (km/h)")
    """The speed (in kilometers per hour) at which the airplane lands."""


fp_config_fields = list(FlightPathConfig.model_fields.keys())
doc = (
    'Many fields are explained in the "Flight path configuration" diagram. '
    f" Fields `{fp_config_fields[0]}` through `{fp_config_fields[-1]}` are shared between the "
    "`airliner_flight_path_config` and the `uavs_flight_path_config` and are described as applying "
    'to an "airplane" rather than to an "airliner" or "UAV" specifically. Fields after that differ.'
)


class AirlinerFlightPathConfig(FlightPathConfig):
    """Configuration of the airliner's flight path."""

    origin_airport_code: AirportCode = Field(title="Origin Airport Code")
    """The three-letter IATA airport code of the origin airport from which the airliner departs."""
    flyover_airport_codes: list[AirportCode] = Field(title="Flyover Airport Codes")
    """The codes of the airports over which the airliner flies to be mid-air refueled by those \
    airports' UAVs.
    """
    destination_airport_code: AirportCode = Field(
        title="Destination Airport Code"
    )
    """The code of the destination airport at which the airliner will land."""
    cruise_altitude_km: float = Field(title="Cruise Altitude (km)")
    """The altitude (in kilometers) of the airliner while in the cruise phase of flight."""
    turning_radius_km: float = Field(title="Turning Radius (km)")
    """The radius (in kilometers) of the arc followed by the airliner over each flyover airport."""
    speed_change_distance_km: float = Field(title="Speed Change Distance (km)")
    """The distance (in kilometers) over which the airliner slows down for refueling (from its \
    cruise speed to the UAVs' cruise speed) or speeds up again after refueling.
    """


AirlinerFlightPathConfig.__doc__ = AirlinerFlightPathConfig.__doc__.strip() + " " + doc


class UavsFlightPathConfig(FlightPathConfig):
    """Configuration of the UAVs' flight paths (all of which are assumed to follow the same \
    parameters).
    A UAV is described as having a "service side". The service side is "to-airport" for UAVs that \
    refuel the airliner just **before** it flies over a given airport, and "from-airport" for UAVs \
    that refuel the airliner just **after** it flies over it.
    """

    smallest_cruise_altitude_km: float = Field(title="Smallest Cruise Altitude (km)")
    """The minimum cruise altitude (in kilometers) among the UAVs. Among the UAVs with \
    "to-airport" service, and among the UAVs with "from-airport" service, this is the actual \
    cruise altitude of the UAV that refuels the airliner first. Subsequent UAVs must cruise at \
    higher altitudes (differing by the `inter_uav_vertical_distance_km`) to stay out of each \
    other's flight paths.
    """
    arc_radius_km: float = Field(title="Arc Radius (km)")
    """The radius (in kilometers) of the arc followed by every UAV in the following cases. For the \
    "to-airport" UAVs, this is the arc followed by the UAV after departing from the airport, when \
    turning around to fly with and refuel the airliner. For the "from-airport" UAVs, this is the \
    arc followed by the UAV after refueling and ascending from the airliner, when turning around \
    to return to the airport.
    """
    airliner_uav_docking_distance_km: float = Field(
        title="Airliner-UAV Docking Distance (km)"
    )
    """The distance (in kilometers) between the airliner and UAV when docked for refueling. \
    Evident when `viz_enabled` is set to true, this is not the distance between the top of the \
    airliner's fueselage and the bottom of the UAV, but the distance between their respective 3D \
    models' origins. This means that if either the airliner's or UAV's 3D models are changed, then \
    the `airliner_uav_docking_distance_km` may need to be changed accordingly.
    """
    smallest_undocking_distance_from_airport_km: float = Field(
        title="Smallest (Un)Docking Distance From Airport (km)"
    )
    """For the "to-airport" UAVs, this is the minimum distance (in kilometers) from the airport at \
    which the UAV will **undock** from the airliner after refueling. For the "from-airport" UAVs, \
    this is the minimum distance from the airport at which the UAV will **dock** with the airliner \
    for refueling. For the UAVs that refuel the airliner closest to a given flyover airport, this \
    is their actual (un)docking distance. For UAVs farther from the airport, their distance is \
    obviously greater.
    """
    inter_uav_clearance_km: float = Field(title="Inter-UAV Clearance (km)")
    """Among the "to-airport" UAVs at a given flyover airport, and among the "from-airport" UAVs \
    at a given flyover airport, this is the distance between one UAV undocking with the airliner \
    and a subsequent UAV docking with it.
    """
    airliner_clearance_speed_kmph: float = Field(
        title="Airliner Clearance Speed (km/h)"
    )
    """After the airliner is refueled once, it must remain at the UAVs' cruise speed for any \
    further refuelings at the same flyover airport. Therefore, after undocking and ascending above \
    the airliner, every UAV must temporarily slow down to this `airliner_clearance_speed_kmph` in \
    order to 'fall behind' it, to allow the UAV to then descend below the airliner's cruise \
    altitude on its way back to the airport, to allow further UAVs to safely refuel the airliner.
    """
    airliner_clearance_distance_km: float = Field(
        title="Airliner Clearance Distance (km)"
    )
    """See `airliner_clearance_speed_kmph`. The `airliner_clearance_distance_km` is the distance \
    (in kilometers) by which every UAV will 'fall behind' the airliner after undocking."""
    smallest_airliner_clearance_altitude_km: float = Field(
        title="Smallest Airliner Clearance Altitude (km)"
    )
    """See `airliner_clearance_speed_kmph`. The `smallest_airliner_clearance_altitude_km` is the \
    minimum altitude (in kilometers) at which the UAVs will fly after descending below the \
    airliner's cruise altitude on its way back to the airport. Among the UAVs with "to-airport" \
    service, and among the UAVs with "from-airport" service, this is the actual airliner clearance \
    altitude of the UAV that refuels the airliner first. Subsequent UAVs must have higher airliner \
    clearance altitudes (differing by the `inter_uav_vertical_distance_km`) to stay out of each \
    other's flight paths.
    """
    inter_uav_vertical_distance_km: float = Field(
        title="Inter-UAV Vertical Distance (km)"
    )
    """See `smallest_cruise_altitude_km` and `smallest_airliner_clearance_altitude_km`."""


UavsFlightPathConfig.__doc__ = UavsFlightPathConfig.__doc__.strip() + " " + doc


class NUavsAtFlyOverAirport(Model):
    """The number of UAVs at a specific airport."""

    to_airport: int = Field(title="To Airport")
    """The number of UAVs to refuel the airliner just before flying over the airport."""
    from_airport: int = Field(title="From Airport")
    """The number of UAVs to refuel the airliner just after flying over the airport."""


UavSpecName = Enum("UavSpecName", {k: k for k in uav_lookup.keys()})
UavVizModelName = Enum("UavVizModelName", {k: k for k in uav_model_lookup.keys()})


class UavsConfig(Model):
    """Configuration of the UAVs (all of which are assumed to be the same)."""

    airplane_spec_name: UavSpecName = Field(title="Airplane Spec Name")
    """Which airplane spec to use for every UAV. Must be one of those listed below. `specs.py` \
    acts as a registry for these and, if a different UAV is desired, a new spec can be added there.
    """
    refueling_rate_kW: float = Field(title="Refueling Rate (kW)")
    """The maximum rate (in kilowatts / joules per second) at which every UAV can refuel the \
    airliner. Can represent refueling at a rate of `x` joules of fuel per second, or recharging at \
    a rate of `x` kilowatts of electricity.
    """
    initial_energy_level_pc: float = Field(title="Initial Energy Level (%)")
    """The amount of energy/fuel that every UAV starts with for **its own use** before takeoff \
    from its airport. Expressed as a percentage (0-100) of the UAV's own energy capacity (based on \
    its own fuel tank space).
    """
    initial_refueling_energy_level_pc: float = Field(
        title="Initial Refueling Energy Level (%)"
    )
    """The amount of energy (alternately, the corresponding amount of fuel) for **refueling the \
    airliner** that every UAV starts with before takeoff from its airport. Expressed as a \
    percentage (0-100) of the UAV's refueling energy capacity (based on its cargo space).
    """
    viz_model_name: UavVizModelName = Field(title="Viz Model Name")
    """Which 3D model to use for every UAV, when `viz_enabled` is set to true. Must be one of those \
    listed below. `viz_models.py` acts as a registry for these and, if a different 3D model is \
    desired, a new one can be added there.
    """

    @property
    def airplane_spec(self) -> UavSpec:
        return uav_lookup[self.airplane_spec_name.name]

    @property
    def viz_model(self) -> ModelConfig:
        return uav_model_lookup[self.viz_model.name]


class Timepoint(Model):
    elapsed_mins: Union[float, str]
    """Minutes into the simulation. Can be either a number or a string containing an algebraic \
    expression with number(s), one of the below-listed variables, and add/subtract operations. In \
    other words, it can be in any of the following formats:

    `{number}`
    `{variable}`
    `{number} +/- {number}`
    `{variable} +/- {number}`

    Valid variables are as follows:

    The following variables are specific to the airliner and can be used regardless of whether the \
    airliner is the airplane being tracked.
    `Airliner_takeoff_point`
    `Airliner_ascended_point`
    `{UAV ID}_on_airliner_docking_point`
    `{UAV ID}_on_airliner_undocking_point`
    `Airliner_curve_over_{flyover airport code}_midpoint`
    `Airliner_descent_point`
    `Airliner_landing_point`
    `Airliner_landed_point`

    The following variables are specific to UAVs and can only be used when a UAV is the airplane \
    being tracked; the following variables refer to that UAV.
    `first_point`
    `takeoff_point`
    `ascended_point`
    `arc_start_point`
    `arc_end_point`
    `descent_to_airliner_point`
    `on_airliner_docking_point`
    `on_airliner_undocking_point`
    `ascended_from_airliner_point`
    `lowering_point`
    `lowered_point`
    `descent_point`
    `landing_point`
    `landed_point`
    """

    def evaluate_elapsed_mins(self, reference_times: dict[str, int]) -> dt.timedelta:
        self.elapsed_mins = eval(str(self.elapsed_mins), reference_times)

    @property
    def value(self) -> float:
        raise NotImplementedError


class Ratepoint(Timepoint):
    time_step_s: float = Field(title="Time Step (s)")
    """The time step (in seconds) with which to advance the simulation time at `elapsed_mins`."""

    @property
    def value(self) -> float:
        return self.time_step_s


class Zoompoint(Timepoint):
    zoom: float = Field(title="Zoom")
    """The zoom level of the visualization at `elapsed_mins`."""

    @property
    def value(self) -> float:
        return self.zoom


class UavsZoompointsConfig(Model):
    """Zoompoints when a UAV is the airplane being tracked."""

    to_airport: list[Zoompoint] = Field(title="To Airport")
    """Zoompoints for a "to-airport" UAV."""
    from_airport: list[Zoompoint] = Field(title="From Airport")
    """Zoompoints for a "from-airport" UAV."""


class ZoompointsConfig(Model):
    """The zoom level of the visualization does not need to be constant. A non-constant zoom level \
    is achieved by specifying zoompoints: the zoom level at different times in the simulation. \
    This allows the zoom to be controlled in a reproduceable way. Each zoompoint specifies a \
    `zoom` level at a specified number of minutes elapsed. Between zoompoints, linear \
    interpolation is used to smoothly transition from one zoom level to the next. A constant zoom \
    can be set by specifying a single zoompoint.
    """

    airliner_zoompoints: list[Zoompoint] = Field(title="Airliner Zoompoints")
    """Zoompoints when the airliner is the airplane being tracked."""
    uavs_zoompoints_config: UavsZoompointsConfig = Field(title="UAVs Zoompoints Config")


class MapViewConfig(Model):
    map_texture_filename: Optional[str] = Field(
        title="Map Texture Filename", default=None
    )
    """Name of the texture image file (e.g., a `.jpg` file) to use as the map view's background. \
    For some reason, this file must be added to `vpython`'s textures folder (e.g., \
    `~/miniconda3/envs/<conda-env-name>/lib/<python-version>/site-packages/vpython/vpython_data/`).
    """
    models_scale_factor: float = Field(title="Models Scale Factor")
    """Scale factor for the 3D models (how much to enlarge them to still be visible in the map \
    view).
    """
    zoom: float = Field(title="Zoom")
    """An override zoom level to use exclusively for the map view."""


class ViewportSize(Model):
    width_px: int = Field(title="Width (px)")
    height_px: int = Field(title="Height (px)")

    @property
    def tuple(self) -> tuple[int, int]:
        return self.width_px, self.height_px


class ScreenPosition(Model):
    x_px: int = Field(title="X-Coordinate (px)")
    """X-coordinate (in pixels) relative to the left edge of the screen."""
    y_px: int = Field(title="Y-Coordinate (px)")
    """Y-coordinate (in pixels) relative to the top edge of the screen."""

    @property
    def to_tuple(self) -> tuple[int, int]:
        return (self.x_px, self.y_px)


class ViewportConfig(Model):
    """Configuration of the viewport in which the 3D visualization is rendered."""
    size: ViewportSize = Field(title="Viewport Size")
    origin: ScreenPosition = Field(title="Origin")
    """The position of the viewport with respect to the top-left corner of your screen. Cannot be \
    set to your liking, but must be set when using the `--record` command-line argument to record \
    the correct region of your screen.
    """

class VizConfig(Model):
    time_step_multiplier: float = Field(title="Time Step Multiplier", default=1.0)
    """A number by which to multiply the time steps specified in the `ratepoints`."""
    max_frame_rate_fps: int = Field(title="Max Frame Rate (FPS)")
    """Maximum frame rate (in frames per second) at which to render the visualization. If updating \
    a frame takes too long, the actual frame rate will be less.
    """
    viewport_config: ViewportConfig = Field(title="Viewport Config")
    theme: Literal["day", "night"] = Field(title="Theme")
    """Color theme to use for the sky and (if no `map_texture_filename` is specified) the ground."""
    zoompoints_enabled: bool = Field(title="Zoompoints Enabled", default=True)
    """Whether to enable the zoompoints. Requires `zoompoints_config` if true. For free zoom \
    (using the scrollwheel over the viewport), set this to false.
    """
    zoompoints_config: Optional[ZoompointsConfig] = Field(
        title="Zoompoints Config", default=None
    )
    landed_uavs_waiting_time_mins: float = Field(
        title="Landed UAVs Waiting Time (Mins)"
    )
    """When tracking a UAV, how long (in minutes) to wait after a flyover airport's last UAV lands \
    before ending that UAV's visualization / starting the next UAV's visualization (depending on \
    which UAV is the airplane being tracked).
    """
    map_texture_filename: Optional[str] = Field(
        title="Map Texture Filename", default=None
    )
    """Name of the texture image file (e.g., a `.jpg` file) to use for the ground. For some \
    reason, this file must be added to `vpython`'s textures folder (e.g., \
    `~/miniconda3/envs/{conda-env-name}/lib/{python-version}/site-packages/vpython/vpython_data/`).
    """
    map_view_config: Optional[MapViewConfig] = Field(title="Map View Config")
    """Configuration to use when `--view=map-view`."""


class SimulationConfig(Model):
    """Configuration for the mid-air refueling simulation."""

    airliner_config: AirlinerConfig = Field(title="Airliner Config")
    airliner_flight_path_config: AirlinerFlightPathConfig = Field(
        title="Airliner Flight Path Config"
    )
    n_uavs_per_flyover_airport: dict[AirportCode, NUavsAtFlyOverAirport] = Field(
        title="# UAVs Per Flyover Airport"
    )
    """The number of UAVs at each flyover airport."""
    uavs_config: UavsConfig = Field(title="UAVs Config")
    uavs_flight_path_config: UavsFlightPathConfig = Field(
        title="UAVs Flight Path Config"
    )
    ratepoints: list[Ratepoint] = Field(title="Ratepoints")
    """The rate at which the simulation advances does not need to be constant. A non-constant rate \
    is achieved by specifying ratepoints: the rate at which to advance the simulation at different \
    times in the simulation. This is most useful when `vis_enabled` is true for speeding up \
    mundane parts of the visualization in a reproduceable way, such as when the airliner is \
    between flyover airports, and slowing down parts of the visualization that are of greater \
    interest or require a finer simulation resolution, such as when the airliner is being \
    refueled. Each ratepoint specifies a `time_step_s` with which to advance the simulation at a \
    specified number of minutes elapsed. Between ratepoints, linear interpolation is used to \
    smoothly transition from one rate to the next. A constant rate can be set by specifying a \
    single ratepoint.
    """
    viz_enabled: bool = Field(title="Viz Enabled", default=True)
    """Whether to visualize the airliner and UAVs in-browser while the simulation runs. Requires \
    `viz_config` if true.
    """
    viz_config: Optional[VizConfig] = Field(title="Viz Config", default=None)
    """Configuration to use when `viz_enabled` is set to true."""

    @classmethod
    def from_yaml(
        cls, dir: Path | str, fname: str = "simulation_config.yml"
    ) -> SimulationConfig:
        return cls(**yaml.safe_load(Path(dir, fname).read_text()))


if __name__ == "__main__":
    simulation_config_schema = SimulationConfig.model_json_schema()
    json.dump(
        simulation_config_schema,
        Path("src/three_d_sim/simulation_config_json_schema.json").open("w"),
        indent=4,
    )
