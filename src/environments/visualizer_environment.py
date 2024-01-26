import dataclasses
from typing import Any, Dict

import matplotlib
import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np

from src.modeling_objects import Geofence
from src.utils.utils import MILLISECONDS_PER_SECOND

from .environment import BaseEnvironment, Environment

MIN_SOC = 0.0
MAX_SOC = 1.0

GEOFENCE_COLOR = "#eeeeee"
CHARGING_SITE_COLOR = "#dddddd"


@dataclasses.dataclass(init=False)
class VisualizerEnvironment(Environment):
    GEOFENCE: Geofence = dataclasses.field(init=False)

    fig: plt.Figure = dataclasses.field(init=False)
    ax: plt.Axes = dataclasses.field(init=False)

    def __post_init__(self):
        super().__post_init__()

        self.GEOFENCE = self.ENVIRONMENT_CONFIG.GEOFENCE

        self.fig, self.ax = plt.subplots(layout="tight")
        self.ax.set_aspect("equal")

    def run(self) -> None:
        """
        Note: Overwrites ``Environment.run``.
        """

        BaseEnvironment.run(self)

        ani = animation.FuncAnimation(
            fig=self.fig,
            func=self._run_iteration,
            frames=40,  # TODO: How to use?
            interval=(self.DELAY_TIME_STEP.total_seconds() * MILLISECONDS_PER_SECOND),
        )
        plt.show()

    def _run_iteration(self, frame) -> None:
        super()._run_iteration()

        self.ax.clear()

        self.ax.set_xlim(self.GEOFENCE.bounds("lat"))
        self.ax.set_ylim(self.GEOFENCE.bounds("lon"))
        self.ax.set_xlabel("Longitude (°)")
        self.ax.set_ylabel("Latitude (°)")

        self.ax.set_title(
            f"EV Taxis Visualization\n{self.ev_taxis_emulator_or_interface.current_timestamp}"
        )

        self._plot_geofence()
        self._plot_charge_points()
        self._plot_charging_sites()
        self._plot_trips()
        self._plot_evs()
        self._plot_legend()

    def _plot_geofence(self) -> None:
        for shapely_polygon in self.GEOFENCE.gseries.geometry[0].geoms:
            x, y = np.array(shapely_polygon.exterior.coords).T
            # self.ax.plot(x, y, color="gray")
            region = plt.Polygon(xy=np.c_[x, y], color=GEOFENCE_COLOR)
            self.ax.add_artist(region)

    def _plot_charging_sites(self) -> None:
        for (
            charging_site
        ) in (
            self.ev_taxis_emulator_or_interface.current_state.charging_sites_state.values()
        ):
            circle_artist = plt.Circle(
                xy=charging_site.xy_coords, radius=0.01, color=CHARGING_SITE_COLOR
            )
            self.ax.add_artist(circle_artist)

    def _plot_charge_points(self) -> None:
        for (
            charging_site
        ) in (
            self.ev_taxis_emulator_or_interface.current_state.charging_sites_state.values()
        ):
            for charge_point in charging_site.charge_points.values():
                plt.plot(
                    *charge_point.xy_coords,
                    **VisualizerEnvironment._cp_attrs_to_marker_attrs(),
                )

    def _plot_evs(self) -> None:
        for ev in self.ev_taxis_emulator_or_interface.current_state.evs_state.values():
            ev_marker_coords = (
                ev.location.xy_coords
                if not ev.is_plugged_in
                else ev.connector.PARENT_CHARGE_POINT_LOCATION.xy_coords
            )
            self.ax.add_artist(
                matplotlib.lines.Line2D(
                    [ev_marker_coords[0]],
                    [ev_marker_coords[1]],
                    **VisualizerEnvironment._ev_attrs_to_marker_attrs(soc=ev.soc),
                )
            )

    def _plot_legend(self) -> None:
        def make_legend_element(**kwargs):
            return matplotlib.lines.Line2D([0], [0], **kwargs)

        legend_elements = [
            matplotlib.patches.Patch(
                facecolor=GEOFENCE_COLOR,
                edgecolor=GEOFENCE_COLOR,
                label="Geofence",
            ),
            make_legend_element(
                color="white",
                marker="o",
                markerfacecolor=CHARGING_SITE_COLOR,
                markersize=16,
                label=f"Charging Site (1+ Charge Points)",
            ),
            make_legend_element(
                **VisualizerEnvironment._cp_attrs_to_marker_attrs(),
                label=f"Charge Point (1+ Connectors)",
            ),
            make_legend_element(
                **VisualizerEnvironment._ev_attrs_to_marker_attrs(soc=MIN_SOC),
                label=f"EV Taxi with SoC ≤ {MIN_SOC * 100}%",
            ),
            make_legend_element(
                **VisualizerEnvironment._ev_attrs_to_marker_attrs(soc=MAX_SOC),
                label=f"EV Taxi with SoC ≥ {MAX_SOC * 100}%",
            ),
        ]
        self.ax.legend(handles=legend_elements, loc="best")

    @staticmethod
    def _cp_attrs_to_marker_attrs() -> Dict[str, Any]:
        return {
            "color": "white",
            "marker": "o",
            "markerfacecolor": "#0000ff",
            "markersize": 12,
        }

    @staticmethod
    def _ev_attrs_to_marker_attrs(soc: float) -> Dict[str, Any]:
        def soc_to_markercolor(soc: float) -> np.ndarray:
            # TODO: Min/max SoC?
            MIN_SOC_RGB = np.array([1, 0, 0])
            MAX_SOC_RGB = np.array([0, 1, 0])
            return MIN_SOC_RGB * (1 - soc) + MAX_SOC_RGB * soc

        return {
            "color": "white",
            "marker": "o",
            "markerfacecolor": soc_to_markercolor(soc),
            "markersize": 8,
        }

    def _plot_trips(self) -> None:
        current_trips = (
            self.ev_taxis_emulator_or_interface.current_state.ongoing_trips_state
        )

        for trip in current_trips.values():
            # self.ax.plot(
            #     *np.c_[trip.ORIGIN.xy_coords, trip.DESTINATION.xy_coords],
            #     color="black"
            # )
            self.ax.annotate(
                xy=trip.DESTINATION.xy_coords,
                xytext=trip.ORIGIN.xy_coords,
                text="",
                arrowprops=dict(arrowstyle="->", color="gray"),
            )
