import argparse
import fnmatch
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.modeling_objects import Airplane
from src.three_d_sim.airplane_waypoints_generation import delay_uavs
from src.three_d_sim.make_airplanes import make_airplanes
from src.three_d_sim.simulation_config_schema import SimulationConfig


def write_airplane_paths(airplanes: list[Airplane]) -> None:
    for airplane in airplanes:
        fpath = Path(f"tmp/airplane_paths/{airplane.id}.csv")
        fpath.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(airplane.all_locations).to_csv(
            fpath,
            header=False,
            index=False,
            float_format="%f",
        )


def write_airplane_tagged_waypoints(airplanes: list[Airplane]) -> None:
    for airplane in airplanes:
        fpath = Path(f"tmp/airplane_tagged_waypoints/{airplane.id}.csv")
        fpath.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(airplane.all_tagged_waypoints).drop(columns=["TAG"]).to_csv(
            fpath,
            header=False,
            index=False,
            float_format="%f",
        )


def viz_airplane_paths(airplanes: list[Airplane]) -> None:
    def _speed_to_color(speed_kmph: float) -> np.array:
        MIN_SPEED_RGB = np.array([0, 0, 1])
        MIN_SPEED_KMPH = 0
        MAX_SPEED_RGB = np.array([1, 0, 0])
        MAX_SPEED_KMPH = 1000
        speed_rgb = (speed_kmph - MIN_SPEED_KMPH) / (
            MAX_SPEED_KMPH - MIN_SPEED_KMPH
        ) * (MAX_SPEED_RGB - MIN_SPEED_RGB) + MIN_SPEED_RGB
        return speed_rgb

    fig = go.Figure()
    for airplane in airplanes:
        speeds_kmph = [wp.DIRECT_APPROACH_SPEED_KMPH for wp in airplane.waypoints]
        all_locations = airplane.all_locations
        pair_segments = list(zip(all_locations[1:], all_locations[:-1]))
        for pair_segment, speed_kmph in zip(pair_segments, speeds_kmph):
            x, y, z = np.c_[pair_segment]
            fig.add_scatter3d(
                x=x,
                y=y,
                z=z,
                line=dict(color=([_speed_to_color(speed_kmph)] * 2), width=4),
                mode="lines",
                showlegend=False,
            )
    fig.layout.scene.aspectmode = "data"
    fig.show()


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="Visualization of Generated Airplane Paths")
    parser.add_argument(
        "--config-dir",
        help="Path containing `simulation_config.yml` file.",
    )
    parser.add_argument(
        "--paths-viz-enabled",
        type=bool,
        default=True,
        help=(
            "Whether to visualize the airplane paths in-browser. Defaults to true. "
            "If set to true, the browser tab opens in your system's default browser. With the "
            "assumption that this is Google Chrome, the program firstly and automatically opens a "
            'new "guest" Chrome window in which this new browser tab will be opened.'
        ),
    )
    parser.add_argument(
        "--airplane-ids",
        default="*",
        help=(
            "The airplane IDs whose airplane paths to visualize. "
            'Supports wildcards ("*"). '
            'For example, "*" (the default) will match all airplane IDs and thus visualize all '
            'airplane paths, while "Airliner,PIT_UAV_*" will visualize only the paths of the '
            "airliner and PIT UAVs."
        ),
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_cli_args()
    simulation_config = SimulationConfig.from_yaml(args.config_dir)
    if args.paths_viz_enabled:
        subprocess.Popen(["google-chrome", "--guest", "--start-maximized"])

    airliner, uavs = make_airplanes(simulation_config)

    flat_uavs = {
        k: {k2: v2 for x in v.values() for k2, v2 in x.items()} for k, v in uavs.items()
    }

    delay_uavs(flat_uavs, airliner)

    airplanes = [airliner] + [
        uav for uav_dict in flat_uavs.values() for uav in uav_dict.values()
    ]

    airplane_id_patterns = [x.strip() for x in args.airplane_ids.split(",")]
    selected_airplanes = [
        a
        for a in airplanes
        if any(fnmatch.fnmatch(a.id, pattern) for pattern in airplane_id_patterns)
    ]

    write_airplane_paths(selected_airplanes)
    write_airplane_tagged_waypoints(selected_airplanes)
    if args.paths_viz_enabled:
        viz_airplane_paths(selected_airplanes)
