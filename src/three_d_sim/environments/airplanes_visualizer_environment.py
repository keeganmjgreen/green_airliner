import dataclasses
import os
from typing import List, Literal, Tuple

import cv2
import numpy as np
import pandas as pd
import pyautogui
import vpython as vp

from environments.environment import BaseEnvironment, Environment
from src.modeling_objects import KM_PER_LAT_LON
from src.three_d_sim.flight_path_generation import (
    FlightPath,
    orthogonal_xy_vector,
)
from src.three_d_sim.models.wavefront_obj_to_vp import (
    simple_wavefront_obj_to_vp,
)
from src.utils.utils import get_interpolator_by_elapsed_time, timedelta_to_minutes
from src.three_d_sim.config_model import Zoompoint

View = Literal["side-view", "tail-view", "map-view"]


Color = Tuple[int, int, int]


@dataclasses.dataclass
class SimulationColorPalette:
    sky: Color
    ground: Color
    airport: Color


palette_lookup = {
    "day": SimulationColorPalette(
        sky=(187, 222, 251),
        ground=(200, 230, 201),
        airport=(189, 189, 189),
    ),
    "night": SimulationColorPalette(
        sky=(26, 35, 126),
        ground=(27, 94, 32),
        airport=(117, 117, 117),
    ),
}

theme = os.environ.get("THEME", "day")
BOUND_KM = 200 * KM_PER_LAT_LON
AIRPORT_RADIUS_KM = 1


_rgb_to_vp_color = lambda rgb: vp.vec(*(np.array(rgb) / 255))


@dataclasses.dataclass
class ScreenRecorder:
    origin: Tuple[int, int]
    size: Tuple[int, int]
    fname: str

    def set_up(self, fps: int):
        self._video_writer = cv2.VideoWriter(
            filename=self.fname,
            fourcc=cv2.VideoWriter_fourcc(*"XVID"),
            fps=fps,
            frameSize=self.size,
        )

    def take_screenshot(self):
        img = pyautogui.screenshot(region=(*self.origin, *self.size))
        frame = np.array(img)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self._video_writer.write(frame)

    def release(self):
        self._video_writer.release()


@dataclasses.dataclass(kw_only=True)
class AirplanesVisualizerEnvironment(Environment):
    AIRLINER_FLIGHT_PATH: FlightPath
    TRACK_AIRPLANE_ID: str
    VIEW: View
    zoompoints: List[Zoompoint]
    SCENE_SIZE: Tuple[int, int] = (1800, 900)
    theme: Literal["day", "night"]
    MODELS_SCALE_FACTOR: float = 1.0
    CAPTIONS: bool = True
    SCREEN_RECORDERS: List[ScreenRecorder] = dataclasses.field(default_factory=list)

    palette: SimulationColorPalette = dataclasses.field(init=False)

    def __post_init__(self):
        super().__post_init__()

        assert pd.Series([zp.elapsed_time for zp in self.zoompoints]).is_monotonic_increasing
        self.zoom_factor_interpolator = get_interpolator_by_elapsed_time(self.zoompoints)

        self.palette = palette_lookup[self.theme]

        for screen_recorder in self.SCREEN_RECORDERS:
            screen_recorder.set_up(fps=int(1 / self.delay_time_step.total_seconds()))

        # vp.scene.title = {
        #     "tail-view": f"{self.TRACK_AIRPLANE_ID} Tail View",
        #     "side-view": f"{self.TRACK_AIRPLANE_ID} Side View",
        #     "map-view": "Map View",
        # }[self.VIEW]
        vp.scene.width, vp.scene.height = self.SCENE_SIZE
        vp.scene.background = _rgb_to_vp_color(self.palette.sky)
        vp.scene.ambient = vp.color.white * 0.5

        self._render_ground()
        self._render_airports()

        airplanes = self.ev_taxis_emulator_or_interface.current_state.airplanes.values()

        self.airplane_vp_objs = {}
        for airplane in airplanes:
            print(f"Rendering {airplane.id}...")
            if self.VIEW == "map-view":
                shininess = 0.3
                color = vp.vector(*([0.8] * 3))
            else:
                shininess = 0.3
                color = vp.color.white
            self.airplane_vp_objs[airplane.id] = simple_wavefront_obj_to_vp(
                airplane.viz_model, shininess=shininess, color=color, make_trail=True, retain=3000
            )
        print("Done rendering airplanes.")

        for vp_obj in self.airplane_vp_objs.values():
            vp_obj.size *= self.MODELS_SCALE_FACTOR

        if self.TRACK_AIRPLANE_ID is not None:
            vp.scene.camera.follow(self.airplane_vp_objs[self.TRACK_AIRPLANE_ID])
        if self.VIEW != "map-view":
            vp.scene.up = vp.vector(0, 0, 1)

        self._set_up_graphs()

    def _render_ground(self):
        if self.VIEW == "map-view":
            texture_file = "Miller_projection_SW-tessellated-vert_distortion_removed-cropped_to_pm_200deg_around_jfk_lax_centroid-fixed-waifu2x.jpg"
        else:
            texture_file = "Miller_projection_SW-tessellated-vert_distortion_removed-cropped_to_pm_200deg_around_jfk_lax_centroid-fixed-gridlines_removed-waifu2x-2x.jpg"
        vp.box(
            pos=vp.vec(0, 0, -0.5 - 0.1),
            length=BOUND_KM,
            width=-1,
            height=BOUND_KM,
            texture=dict(
                file=texture_file,
                flipx=True,
            ),
            shininess=0,
            # Open textures folder using:
            #     nautilus ~/miniconda3/envs/electric_airline/lib/python3.12/site-packages/vpython/vpython_data/
        )
        vp.scene.waitfor("textures")
        # vp.quad(
        #     vs=[
        #         vp.vertex(
        #             pos=vp.vec(*(np.array(xy) * BOUND_KM), -0.1),
        #             color=_rgb_to_vp_color(self.palette.ground),
        #             shininess=0,
        #         )
        #         for xy in [[1, 1], [-1, 1], [-1, -1], [1, -1]]
        #     ]
        # )

    def _render_airports(self):
        airports = self.AIRLINER_FLIGHT_PATH.airports
        # x_coords = [loc.X_KM for loc in airports]
        # y_coords = [loc.Y_KM for loc in airports]
        # center = vp.vector(
        #     *[(max(coords) - min(coords)) / 2 for coords in [x_coords, y_coords]], 0
        # )
        for airport in airports:
            cr = vp.shapes.circle(pos=list(airport.xy_coords), radius=AIRPORT_RADIUS_KM)
            for i in range(len(cr)):
                vs = [airport.xy_coords, cr[i - 1], cr[i]]
                vp.triangle(
                    vs=[
                        vp.vertex(
                            pos=vp.vector(*v, -0.01),
                            color=_rgb_to_vp_color(self.palette.airport),
                        )
                        for v in vs
                    ]
                )

    def _set_up_graphs(self) -> None:
        self.airliner_energy_level_graph = vp.graph(
            title="Airliner Energy Level", xtitle="Time [min]", ytitle="Energy Level (%)", ymin=0, ymax=1, fast=False
        )
        self.airliner_energy_level_gcurve = vp.gcurve()
        self.airliner_speed_graph = vp.graph(
            title="Airliner Speed", xtitle="Time [min]", ytitle="Speed [kmph]", ymin=0, ymax=1e3, fast=False
        )
        self.airliner_speed_gcurve = vp.gcurve()

    def run(self) -> None:
        """
        Note: Overwrites ``Environment.run``.
        """

        BaseEnvironment.run(self)

        while True:
            if self.end_time is not None:
                if self.current_time >= self.end_time:
                    break
            self._run_iteration()

    def _run_iteration(self) -> None:
        super()._run_iteration()

        if self.current_time >= self.skip_timedelta:
            vp.scene.title = str(self.current_time).split(".")[0]
            self._update_airplanes_viz()
            self._update_graphs()
            for screen_recorder in self.SCREEN_RECORDERS:
                screen_recorder.take_screenshot()
            vp.rate(1 / self.delay_time_step.total_seconds())

    def _update_airplanes_viz(self) -> None:
        zoom_factor = self.zoom_factor_interpolator(
            self.current_time
        )
        print(f"zoom_factor: {zoom_factor:.2f}")
        vp.scene.range = self.MODELS_SCALE_FACTOR / zoom_factor

        evs_state = self.ev_taxis_emulator_or_interface.current_state.airplanes
        for ev in evs_state.values():
            self.airplane_vp_objs[ev.id].pos = vp.vector(
                *ev.location.xyz_coords
            ) + vp.vec(*ev.viz_model.TRANSLATION_VECTOR)
            if self.VIEW == "map-view":
                self.airplane_vp_objs[ev.id].pos.z *= 10
                self.airplane_vp_objs[ev.id].pos.z += 200
            self.airplane_vp_objs[ev.id].axis = vp.vector(*ev.heading)
        if self.VIEW != "map-view":
            heading = evs_state[self.TRACK_AIRPLANE_ID].heading
            heading[2] = 0
            heading = heading / np.linalg.norm(heading)
            heading[2] = -0.3
            if self.VIEW == "tail-view":
                vp.scene.forward = vp.vector(*heading)
            elif self.VIEW == "side-view":
                vp.scene.forward = vp.vector(*orthogonal_xy_vector(heading))
        if self.CAPTIONS:
            vp.scene.caption = "\n" + "\n".join([str(ev) for ev in evs_state.values()])

    def _update_graphs(self) -> None:
        minutes_elapsed = timedelta_to_minutes(self.current_time)
        evs_state = self.ev_taxis_emulator_or_interface.current_state.airplanes
        self.airliner_energy_level_gcurve.plot(
            minutes_elapsed,
            evs_state["Airliner"].energy_level_pc,
        )
        airliner_waypoints = evs_state["Airliner"].waypoints
        self.airliner_speed_gcurve.plot(
            minutes_elapsed,
            airliner_waypoints[0].DIRECT_APPROACH_SPEED_KMPH if len(airliner_waypoints) > 0 else 0
        )