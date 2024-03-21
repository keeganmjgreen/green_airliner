import dataclasses
from typing import Literal

import numpy as np
import vpython as vp

from src.environments import BaseEnvironment, Environment
from src.three_d_sim.flight_path_generation import (
    FlightPath,
    orthogonal_xy_vector,
)
from src.three_d_sim.models.wavefront_obj_to_vp import (
    simple_wavefront_obj_to_vp,
)
from src.utils.utils import _getenv, timedelta_to_minutes

VIEW_TYPE = Literal["airplane-side-view", "airplane-tail-view"]

N_VIEW_COLUMNS = 2
SCENE_WIDTH = 1800
SCENE_HEIGHT = 900

theme = _getenv("THEME", default_val="day")
if theme == "day":
    SKY_RGB_COLOR = [187, 222, 251]
    GROUND_RGB_COLOR = [200, 230, 201]
    AIRPORT_COLOR = [189] * 3
elif theme == "night":
    SKY_RGB_COLOR = [26, 35, 126]
    GROUND_RGB_COLOR = [27, 94, 32]
    AIRPORT_COLOR = [117] * 3
BOUND_KM = 1e4
AIRPORT_RADIUS_KM = 1

MIN_SOC = 0.0
MAX_SOC = 1.0


_rgb_to_vp_color = lambda rgb: vp.vec(*(np.array(rgb) / 255))


@dataclasses.dataclass(kw_only=True)
class AirplanesVisualizerEnvironment(Environment):
    AIRLINER_FLIGHT_PATH: FlightPath
    TRACK_AIRPLANE_ID: str
    VIEW: VIEW_TYPE
    N_VIEW_COLUMNS: int = 1
    MODELS_SCALE_FACTOR: float = 1.0

    def __post_init__(self):
        super().__post_init__()

        vp.scene.title = {
            "airplane-tail-view": f"{self.TRACK_AIRPLANE_ID} Tail View",
            "airplane-side-view": f"{self.TRACK_AIRPLANE_ID} Side View",
        }[self.VIEW]
        vp.scene.width, vp.scene.height = (
            SCENE_WIDTH / self.N_VIEW_COLUMNS,
            SCENE_HEIGHT,
        )
        vp.scene.background = _rgb_to_vp_color(SKY_RGB_COLOR)

        vp.quad(
            vs=[
                vp.vertex(
                    pos=vp.vec(*(np.array(xy) * BOUND_KM), -0.1),
                    color=_rgb_to_vp_color(GROUND_RGB_COLOR),
                    shininess=0,
                )
                for xy in [[1, 1], [-1, 1], [-1, -1], [1, -1]]
            ]
        )

        airport_locations = self.AIRLINER_FLIGHT_PATH.AIRPORT_LOCATIONS
        # x_coords = [loc.X_KM for loc in airport_locations]
        # y_coords = [loc.Y_KM for loc in airport_locations]
        # center = vp.vector(
        #     *[(max(coords) - min(coords)) / 2 for coords in [x_coords, y_coords]], 0
        # )
        for loc in airport_locations:
            cr = vp.shapes.circle(
                pos=list(loc.xy_coords),
                radius=(AIRPORT_RADIUS_KM * self.MODELS_SCALE_FACTOR),
            )
            for i in range(len(cr)):
                vs = [loc.xy_coords, cr[i - 1], cr[i]]
                vp.triangle(
                    vs=[
                        vp.vertex(
                            pos=vp.vector(*v, -0.01), color=_rgb_to_vp_color(AIRPORT_COLOR)
                        )
                        for v in vs
                    ]
                )

        airplanes = self.ev_taxis_emulator_or_interface.current_state.evs_state.values()

        self.airplane_vp_objs = {}
        for airplane in airplanes:
            print(f"Rendering {airplane.ID}...")
            self.airplane_vp_objs[airplane.ID] = simple_wavefront_obj_to_vp(
                airplane.MODEL_CONFIG, make_trail=True, retain=2000
            )
        print("Done rendering airplanes.")

        for vp_obj in self.airplane_vp_objs.values():
            vp_obj.size *= self.MODELS_SCALE_FACTOR

        vp.scene.camera.follow(self.airplane_vp_objs[self.TRACK_AIRPLANE_ID])
        vp.scene.up = vp.vector(0, 0, 1)
        vp.scene.range = 0.2 * self.MODELS_SCALE_FACTOR

        self._set_up_graphs()

    def _set_up_graphs(self) -> None:
        self.airliner_soc_graph = vp.graph(title="Airliner SoC", xtitle="Time [min]", ytitle="SoC", ymin=0, ymax=1)
        self.airliner_soc_gcurve = vp.gcurve()
        self.airliner_speed_graph = vp.graph(title="Airliner Speed", xtitle="Time [min]", ytitle="Speed [kmph]", ymin=0, ymax=1e3)
        self.airliner_speed_gcurve = vp.gcurve()

    def run(self) -> None:
        """
        Note: Overwrites ``Environment.run``.
        """

        BaseEnvironment.run(self)

        while True:
            self._run_iteration()

    def _run_iteration(self) -> None:
        super()._run_iteration()

        if self.current_timestamp >= self.START_TIMESTAMP + self.SKIP_TIMEDELTA:
            self._update_airplanes_viz()
            self._update_graphs()
            vp.rate(1 / self.DELAY_TIME_STEP.total_seconds())

    def _update_airplanes_viz(self) -> None:
        evs_state = self.ev_taxis_emulator_or_interface.current_state.evs_state
        for ev in evs_state.values():
            self.airplane_vp_objs[ev.ID].pos = vp.vector(
                *ev.location.xyz_coords
            ) + vp.vec(*ev.MODEL_CONFIG.TRANSLATION_VECTOR)
            self.airplane_vp_objs[ev.ID].axis = vp.vector(*ev.heading)
        heading = evs_state[self.TRACK_AIRPLANE_ID].heading
        heading[2] = 0
        heading = heading / np.linalg.norm(heading)
        heading[2] = -0.3
        if self.VIEW == "airplane-tail-view":
            vp.scene.forward = vp.vector(*heading)
        elif self.VIEW == "airplane-side-view":
            vp.scene.forward = vp.vector(*orthogonal_xy_vector(heading))
        vp.scene.caption = "\n" + "\n".join([str(ev) for ev in evs_state.values()])

    def _update_graphs(self) -> None:
        minutes_elapsed = timedelta_to_minutes(self.current_timestamp - self.START_TIMESTAMP)
        evs_state = self.ev_taxis_emulator_or_interface.current_state.evs_state
        self.airliner_soc_gcurve.plot(
            minutes_elapsed,
            evs_state["Airliner"].soc,
        )
        airliner_waypoints = evs_state["Airliner"].waypoints
        self.airliner_speed_gcurve.plot(
            minutes_elapsed,
            airliner_waypoints[0].DIRECT_APPROACH_SPEED_KMPH if len(airliner_waypoints) > 0 else 0
        )