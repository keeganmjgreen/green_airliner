import argparse
import datetime as dt
import os
import subprocess
from typing import Literal

from src.airplanes_simulator import AirplanesSimulator
from src.modeling_objects import AirplanesState
from src.three_d_sim.airplane_waypoints_generation import delay_uavs
from src.three_d_sim.environments.airplanes_visualizer_environment import (
    AirplanesVisualizerEnvironment,
    ScreenRecorder,
    View,
)
from src.three_d_sim.make_airplanes import make_airplanes
from src.three_d_sim.simulation_config_schema import (
    SimulationConfig,
    ViewportSize,
    Zoompoint,
)
from src.utils.utils import timedelta_to_minutes


def run_scenario(
    simulation_config: SimulationConfig,
    view: View,
    track_airplane_id: str,
    record: Literal["airplanes-viz", "graphs"],
) -> None:
    airliner, uavs = make_airplanes(simulation_config)

    flat_uavs = {
        k: {k2: v2 for x in v.values() for k2, v2 in x.items()} for k, v in uavs.items()
    }

    delay_uavs(flat_uavs, airliner)

    airplanes = [airliner] + [
        uav for uav_dict in flat_uavs.values() for uav in uav_dict.values()
    ]

    airplanes_emulator = AirplanesSimulator(
        initial_state=AirplanesState(
            airplanes={airplane.id: airplane for airplane in airplanes},
        ),
    )

    skip_timedelta = dt.timedelta(minutes=0)
    airliner_reference_times = airliner.get_elapsed_time_at_tagged_waypoints()
    airliner_reference_times = {
        k: timedelta_to_minutes(v) for k, v in airliner_reference_times.items()
    }
    for airport in airliner.flight_path.flyover_airports:
        airliner_reference_times[f"Airliner_curve_over_{airport.CODE}_midpoint"] = (
            airliner_reference_times[f"Airliner_curve_over_{airport.CODE}_start_point"]
            + airliner_reference_times[f"Airliner_curve_over_{airport.CODE}_end_point"]
        ) / 2
    if view != "map-view":
        assert track_airplane_id is not None
        models_scale_factor = 1
        if track_airplane_id == "Airliner":
            zoompoints = (
                simulation_config.viz_config.zoompoints_config.airliner_zoompoints
            )
            for zp in zoompoints:
                zp.evaluate_elapsed_mins(airliner_reference_times)
        else:
            uav_id = track_airplane_id
            uav_airport_code = track_airplane_id[:3]
            service_side = (
                "to_airport"
                if uav_id in uavs[uav_airport_code]["to_airport"]
                else "from_airport"
            )
            uav_reference_times = uavs[uav_airport_code][service_side][
                uav_id
            ].get_elapsed_time_at_tagged_waypoints()
            uav_reference_times = {
                k.removeprefix(f"{track_airplane_id}_"): timedelta_to_minutes(v)
                for k, v in uav_reference_times.items()
            }

            airport_last_uav_id = list(uavs[uav_airport_code]["from_airport"].keys())[
                -1
            ]
            airport_last_uav_td = uavs[uav_airport_code]["from_airport"][
                airport_last_uav_id
            ].get_elapsed_time_at_tagged_waypoints()[
                f"{airport_last_uav_id}_landed_point"
            ]

            uavs_zoompoints_config = (
                simulation_config.viz_config.zoompoints_config.uavs_zoompoints_config
            )
            zoompoints = {
                "to_airport": uavs_zoompoints_config.to_airport,
                "from_airport": uavs_zoompoints_config.from_airport,
            }[service_side]
            zoompoints.append(
                Zoompoint(
                    elapsed_mins=(
                        timedelta_to_minutes(airport_last_uav_td)
                        + simulation_config.viz_config.landed_uavs_waiting_time_mins
                    ),
                    zoom=zoompoints[-1].zoom,
                )
            )
            for zp in zoompoints:
                zp.evaluate_elapsed_mins(uav_reference_times)

            if uav_airport_code != airliner.flight_path.flyover_airports[0].CODE:
                previous_airport = airliner.flight_path.flyover_airports[
                    airliner.flight_path.flyover_airport_codes.index(uav_airport_code)
                    - 1
                ]
                previous_uav = (
                    list(uavs[previous_airport.CODE]["to_airport"].values())
                    + list(uavs[previous_airport.CODE]["from_airport"].values())
                )[-1]
                skip_timedelta = previous_uav.get_elapsed_time_at_tagged_waypoints()[
                    f"{previous_uav.id}_landed_point"
                ] + dt.timedelta(
                    minutes=(simulation_config.viz_config.landed_uavs_waiting_time_mins)
                )
    else:
        models_scale_factor = (
            simulation_config.viz_config.map_view_config.models_scale_factor
        )
        zoompoints = [
            Zoompoint(0, zoom=simulation_config.viz_config.map_view_config.zoom)
        ]

    viewport_size = simulation_config.viz_config.viewport_config.size.tuple
    viewport_origin = simulation_config.viz_config.viewport_config.origin
    captions = True
    if record == "airplanes-viz":
        video_dir = os.environ["VIDEO_DIR"]
        screen_recorders = [
            ScreenRecorder(
                origin=viewport_origin,
                size=viewport_size,
                fname=f"{video_dir}/inputs/{track_airplane_id or ''}-{view}.avi",
            )
        ]
    elif record == "graphs":
        captions = False
        video_dir = os.environ["VIDEO_DIR"]
        viewport_size = ViewportSize(
            width_px=180, height_px=90
        )  # Make room for graphs.
        VERTICAL_OFFSET_PX = viewport_origin.y_px + viewport_size.height_px + 1
        graph_size = ViewportSize(width_px=640, height_px=445)
        screen_recorders = [
            ScreenRecorder(
                origin=(viewport_origin.x_px, VERTICAL_OFFSET_PX),
                size=graph_size.tuple,
                fname=f"{video_dir}/inputs/Airliner-energy-level-graph.avi",
            ),
            ScreenRecorder(
                origin=(
                    viewport_origin.x_px,
                    VERTICAL_OFFSET_PX + graph_size.height_px,
                ),
                size=graph_size.tuple,
                fname=f"{video_dir}/inputs/Airliner-speed-graph.avi",
            ),
        ]
    else:
        screen_recorders = []

    reference_times = airliner_reference_times
    if "uav_reference_times" in locals():
        reference_times.update(uav_reference_times)
    for rp in simulation_config.ratepoints:
        rp.evaluate_elapsed_mins(reference_times)

    environment = AirplanesVisualizerEnvironment(
        ratepoints=simulation_config.ratepoints,
        max_frame_rate_fps=simulation_config.viz_config.max_frame_rate_fps,
        skip_timedelta=skip_timedelta,
        end_time=dt.timedelta(minutes=zoompoints[-1].elapsed_mins),
        ev_taxis_emulator_or_interface=airplanes_emulator,
        airports=airliner.flight_path.airports,
        track_airplane_id=track_airplane_id,
        view=view,
        map_texture_fpath=(
            simulation_config.viz_config.map_view_config.map_texture_filename
            if view == "map-view"
            else simulation_config.viz_config.map_texture_filename
        ),
        zoompoints=zoompoints,
        viewport_size=viewport_size,
        theme=simulation_config.viz_config.theme,
        models_scale_factor=models_scale_factor,
        captions=captions,
        screen_recorders=screen_recorders,
    )
    environment.run()
    for screen_recorder in screen_recorders:
        screen_recorder.release()
    quit()


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir")
    parser.add_argument("--view")
    parser.add_argument("--track-airplane-id", default=None)
    parser.add_argument("--record", default=None)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_cli_args()
    simulation_config = SimulationConfig.from_yaml(args.config_dir)
    if simulation_config.viz_enabled:
        subprocess.Popen(["google-chrome", "--guest", "--start-maximized"])
    run_scenario(
        simulation_config=simulation_config,
        view=args.view,
        track_airplane_id=args.track_airplane_id,
        record=args.record,
    )
