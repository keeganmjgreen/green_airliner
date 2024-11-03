import argparse
import datetime as dt
import subprocess
from typing import Dict

from src.feasibility_study.modeling_objects import Fuel
from src import specs
from src.airplanes_simulator import AirplanesSimulator
from src.environments import EnvironmentConfig
from src.modeling_objects import Airliner, AirplanesState, Uav
from src.three_d_sim.airplanes_visualizer_environment import (
    View,
    AirplanesVisualizerEnvironment,
    ScreenRecorder,
)
from src.three_d_sim.config_model import SimulationConfig
from src.three_d_sim.flight_path_generation import (
    AirlinerFlightPath,
    UavFlightPath,
    delay_uavs,
    provision_airliner_from_flight_path,
    provision_uav_from_flight_path,
    viz_airplane_paths,
)
from src.utils.utils import (
    J_PER_MJ,
    J_PER_WH,
    SECONDS_PER_HOUR,
    _getenv,
    timedelta_to_minutes,
)


def run_scenario(
    simulation_config: SimulationConfig, view: View, track_airplane_id: str, preset: str
) -> None:
    airliner = Airliner(**simulation_config.airliner_config)
    airliner_fp = AirlinerFlightPath(
        **simulation_config.airliner_flight_path_config,
        cruise_speed_kmph=airliner.airplane_spec.cruise_speed_kmph,
    )

    uavs = make_uavs(
        simulation_config, fuel=airliner.airplane_spec.fuel, airliner_fp=airliner_fp
    )

    flat_uavs = {
        k: {k2: v2 for x in v.values() for k2, v2 in x.items()} for k, v in uavs.items()
    }

    delay_uavs(flat_uavs, airliner)

    airplanes = [airliner] + [
        uav for uav_dict in flat_uavs.values() for uav in uav_dict.values()
    ]

    if view == "airplane-paths":
        viz_airplane_paths(airplanes)
        quit()

    airplanes_emulator = AirplanesSimulator(
        initial_state=AirplanesState(
            airplanes={airplane.id: airplane for airplane in airplanes},
        ),
    )

    skip_timedelta = dt.timedelta(minutes=0)
    d_airliner = airliner.get_elapsed_time_at_tagged_waypoints()
    d_airliner = {k: timedelta_to_minutes(v) for k, v in d_airliner.items()}
    for airport_code in ["PIT", "DEN"]:
        d_airliner[f"Airliner-curve-over-{airport_code}-midpoint"] = (
            d_airliner[f"Airliner-curve-over-{airport_code}-start-point"]
            + d_airliner[f"Airliner-curve-over-{airport_code}-end-point"]
        ) / 2
    if view != "map-view":
        assert track_airplane_id is not None
        models_scale_factor = 1
        if track_airplane_id == "Airliner":
            d = d_airliner
            zoom = [
                (eval(zp.elapsed_minutes), zp.zoom)
                for zp in simulation_config.viz_config.zoompoints_config.airliner_zoompoints
            ]
        else:
            uav_id = track_airplane_id
            uav_airport_code = track_airplane_id[:3]
            service_side = "to-airport" if uav_id in uavs[uav_airport_code]["to-airport"] else "from-airport"
            d = uavs[uav_airport_code][service_side][uav_id].get_elapsed_time_at_tagged_waypoints()
            d = {k.removeprefix(f"{track_airplane_id}-").removesuffix("-point"): timedelta_to_minutes(v) for k, v in d.items()}

            airport_last_uav_id = list(uavs[uav_airport_code]["from-airport"].keys())[-1]
            airport_last_uav_td = uavs[uav_airport_code]["from-airport"][airport_last_uav_id].get_elapsed_time_at_tagged_waypoints()[f"{airport_last_uav_id}-landed-point"]

            CORRECTION_MINS = (60 + 47) / SECONDS_PER_HOUR

            if service_side == "to-airport":
                zoom = [
                    (eval(zp.elapsed_minutes), zp.zoom)
                    for zp in simulation_config.viz_config.zoompoints_config.uavs_zoompoints_config.to_airport
                ]
                zoom.append((timedelta_to_minutes(airport_last_uav_td) + simulation_config.viz_config.landed_uavs_waiting_time_mins, zoom[-1][1]))
            else:
                zoom = [
                    (eval(zp.elapsed_minutes), zp.zoom)
                    for zp in simulation_config.viz_config.zoompoints_config.uavs_zoompoints_config.from_airport
                ]
                zoom.append((timedelta_to_minutes(airport_last_uav_td) + simulation_config.viz_config.landed_uavs_waiting_time_mins, zoom[-1][1]))
            if uav_airport_code != "PIT":
                last_pit_uav_id = list(uavs["PIT"]["from-airport"].keys())[-1]
                skip_timedelta = uavs["PIT"]["from-airport"][last_pit_uav_id].get_elapsed_time_at_tagged_waypoints()[f"{last_pit_uav_id}-landed-point"] + dt.timedelta(minutes=(LANDED_UAVS_WAITING_TIME_MINS - CORRECTION_MINS))
                # first_den_uav_id = list(uavs["DEN"]["to-airport"].keys())[0]
                # skip_timedelta = uavs["DEN"]["to-airport"][first_den_uav_id].get_elapsed_time_at_tagged_waypoints()[f"{first_den_uav_id}-first-point"] - dt.timedelta(minutes=2)
    else:
        models_scale_factor = simulation_config.viz_config.map_view_config.models_scale_factor
        zoom = simulation_config.viz_config.map_view_config.zoom

    scene_size = simulation_config.viz_config.scene_size
    captions = True
    if preset == "record-airplanes-viz":
        video_dir = _getenv("VIDEO_DIR", handling="raise")
        screen_recorders = [
            ScreenRecorder(
                origin=(8, 138),
                size=scene_size,
                fname=f"{video_dir}/inputs/{track_airplane_id or ''}-{view}.avi",
            )
        ]
    elif preset == "record-graphs":
        video_dir = _getenv("VIDEO_DIR", handling="raise")
        scene_size = (180, 90)
        captions = False
        OFFSET_H = 229 # 228
        GRAPH_H = 445 # 426
        screen_recorders = [
            ScreenRecorder(
                origin=(8, OFFSET_H),
                size=(640, GRAPH_H),
                fname=f"{video_dir}/inputs/Airliner-energy-level-graph.avi",
            ),
            ScreenRecorder(
                origin=(8, OFFSET_H + GRAPH_H),
                size=(640, GRAPH_H),
                fname=f"{video_dir}/inputs/Airliner-speed-graph.avi",
            ),
        ]
    else:
        screen_recorders = []

    start_timestamp = dt.datetime(2000, 1, 1, 0, 0)
    environment = AirplanesVisualizerEnvironment(
        ENVIRONMENT_CONFIG=EnvironmentConfig(
            TIME_STEP=simulation_config.ratepoints,
            DELAY_TIME_STEP=simulation_config.viz_config.min_frame_duration_s,
            START_TIMESTAMP=start_timestamp,
            SKIP_TIMEDELTA=skip_timedelta,
            END_TIMESTAMP=(start_timestamp + dt.timedelta(minutes=zoom[-1][0])),
        ),
        ev_taxis_emulator_or_interface=airplanes_emulator,
        AIRLINER_FLIGHT_PATH=airliner_fp,
        TRACK_AIRPLANE_ID=track_airplane_id,
        VIEW=view,
        ZOOM=zoom,
        SCENE_SIZE=scene_size,
        MODELS_SCALE_FACTOR=models_scale_factor,
        CAPTIONS=captions,
        SCREEN_RECORDERS=screen_recorders,
    )
    environment.run()
    for screen_recorder in screen_recorders:
        screen_recorder.release()
    quit()


def make_uavs(
    simulation_config: SimulationConfig, fuel: Fuel, airliner_fp: AirlinerFlightPath
) -> Dict[str, Dict[str, Dict[str, Uav]]]:
    uavs = {}
    uav_fps = {}
    for uav_airport_code, x in simulation_config.n_uavs_per_flyover_airport.items():
        airport_uav_idx = 0
        uavs[uav_airport_code] = {}
        uav_fps[uav_airport_code] = {}
        for service_side, n_uavs in x.items():
            uavs[uav_airport_code][service_side] = {}
            uav_fps[uav_airport_code][service_side] = {}
            for service_side_uav_idx in range(n_uavs):
                # Instantiate the UAV:
                uav = Uav(
                    id=f"{uav_airport_code}-UAV-{airport_uav_idx}",
                    **simulation_config.uavs_config,
                    payload_fuel=fuel,
                )
                # Add the UAV to the `uavs` dict:
                uavs[uav_airport_code][service_side][uav.id] = uav

                refueling_rate_kW = min(
                    simulation_config.airliner_config["refueling_rate_kW"],
                    simulation_config.uavs_config["refueling_rate_kW"],
                )
                refueling_distance_km = (
                    uav.airplane_spec.cruise_speed_kmph
                    * (uav.refueling_energy_capacity_MJ * J_PER_MJ / J_PER_WH)
                    / refueling_rate_kW
                )
                decreasing_towards_airport = (
                    service_side_uav_idx
                    if service_side == "from-airport"
                    else (n_uavs - service_side_uav_idx - 1)
                )
                uavs_fp_config = simulation_config.uavs_flight_path_config
                # Instantiate the UAV Flight Path:
                uav_fp = UavFlightPath(
                    airport_codes=[uav_airport_code],
                    cruise_altitude_km=(
                        uavs_fp_config["default_cruise_altitude_km"]
                        + uavs_fp_config["inter_uav_vertical_dist_km"]
                        * service_side_uav_idx
                    ),
                    cruise_speed_kmph=uav.airplane_spec.cruise_speed_kmph,
                    turning_radius_km=airliner_fp.turning_radius_km,
                    refueling_altitude_km=(
                        airliner_fp.cruise_altitude_km
                        + uavs_fp_config["airliner_uav_docking_distance_km"]
                    ),
                    refueling_distance_km=refueling_distance_km,
                    service_side=service_side,
                    undocking_distance_from_airport_km=(
                        uavs_fp_config["undocking_distance_from_airport_km"]
                        + (
                            refueling_distance_km
                            + uavs_fp_config["inter_uav_clearance_km"]
                        )
                        * decreasing_towards_airport
                    ),
                    airliner_clearance_speed_kmph=uavs_fp_config[
                        "airliner_clearance_speed_kmph"
                    ],
                    airliner_clearance_distance_km=uavs_fp_config[
                        "airliner_clearance_distance_km"
                    ],
                    airliner_clearance_altitude_km=(
                        uavs_fp_config["default_airliner_clearance_altitude_km"]
                        + uavs_fp_config["inter_uav_vertical_dist_km"]
                        * service_side_uav_idx
                    ),
                )
                # Add the UAV Flight Path to the `uav_fps` dict:
                uav_fps[uav_airport_code][service_side][uav.id] = uav_fp

                provision_uav_from_flight_path(
                    uav, service_side_uav_idx, n_uavs, uav_fp, airliner_fp
                )

                airport_uav_idx += 1

    provision_airliner_from_flight_path(airliner, airliner_fp, uavs, uav_fps)

    return uavs


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir")
    parser.add_argument("--view")
    parser.add_argument("--track-airplane-id", default=None)
    parser.add_argument("--preset", default=None)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_cli_args()
    # subprocess.Popen(["google-chrome", "--guest", "--start-maximized"])
    run_scenario(
        simulation_config=SimulationConfig.from_yaml(args.config_dir),
        view=args.view,
        track_airplane_id=args.track_airplane_id,
        preset=args.preset,
    )
