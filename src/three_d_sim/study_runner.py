import argparse
import dataclasses
import datetime as dt
import os
import subprocess
from typing import Dict, Tuple

from src.feasibility_study.modeling_objects import Fuel
from src.airplanes_simulator import AirplanesSimulator
from src.modeling_objects import Airliner, AirplanesState, Uav
from src.three_d_sim.environments.airplanes_visualizer_environment import (
    View,
    AirplanesVisualizerEnvironment,
    ScreenRecorder,
)
from src.three_d_sim.simulation_config_schema import SimulationConfig, Zoompoint
from src.three_d_sim.flight_path_generation import (
    AirlinerFlightPath,
    UavFlightPath,
    delay_uavs,
    provision_airliner_from_flight_path,
    provision_uav_from_flight_path,
    viz_airplane_paths,
)
from src.utils.utils import MJ_PER_KWH, timedelta_to_minutes


def run_scenario(
    simulation_config: SimulationConfig, view: View, track_airplane_id: str, preset: str
) -> None:
    airliner_config = simulation_config.airliner_config
    airliner = Airliner(
        airplane_spec=airliner_config.airplane_spec_name,
        refueling_rate_kW=airliner_config.refueling_rate_kW,
        initial_energy_level_pc=airliner_config.initial_energy_level_pc,
        viz_model=airliner_config.viz_model_name,
    )
    airliner_fp_config = simulation_config.airliner_flight_path_config
    airliner_fp = AirlinerFlightPath(
        origin_airport=airliner_fp_config.origin_airport_code,
        flyover_airports=airliner_fp_config.flyover_airport_codes,
        destination_airport=airliner_fp_config.destination_airport_code,
        takeoff_speed_kmph=airliner_fp_config.takeoff_speed_kmph,
        takeoff_distance_km=airliner_fp_config.takeoff_distance_km,
        takeoff_leveling_distance_km=airliner_fp_config.takeoff_leveling_distance_km,
        rate_of_climb_mps=airliner_fp_config.rate_of_climb_mps,
        climb_leveling_distance_km=airliner_fp_config.climb_leveling_distance_km,
        cruise_altitude_km=airliner_fp_config.cruise_altitude_km,
        cruise_speed_kmph=airliner.airplane_spec.cruise_speed_kmph,
        speed_change_distance_km=airliner_fp_config.speed_change_distance_km,
        turning_radius_km=airliner_fp_config.turning_radius_km,
        descent_leveling_distance_km=airliner_fp_config.descent_leveling_distance_km,
        rate_of_descent_mps=airliner_fp_config.rate_of_descent_mps,
        landing_leveling_distance_km=airliner_fp_config.landing_leveling_distance_km,
        landing_distance_km=airliner_fp_config.landing_distance_km,
        landing_speed_kmph=airliner_fp_config.landing_speed_kmph,
    )

    uavs, uav_fps = make_uavs(
        simulation_config, fuel=airliner.airplane_spec.fuel, airliner_fp=airliner_fp
    )

    provision_airliner_from_flight_path(airliner, airliner_fp, uavs, uav_fps)

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
    airliner_reference_times = airliner.get_elapsed_time_at_tagged_waypoints()
    airliner_reference_times = {
        k: timedelta_to_minutes(v) for k, v in airliner_reference_times.items()
    }
    for airport in airliner_fp.flyover_airports:
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

            if uav_airport_code != airliner_fp.flyover_airports[0].CODE:
                previous_airport = airliner_fp.flyover_airports[
                    airliner_fp.flyover_airport_codes.index(uav_airport_code) - 1
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

    scene_size = simulation_config.viz_config.scene_size
    captions = True
    if preset == "record-airplanes-viz":
        video_dir = os.environ["VIDEO_DIR"]
        screen_recorders = [
            ScreenRecorder(
                origin=(8, 138),
                size=scene_size,
                fname=f"{video_dir}/inputs/{track_airplane_id or ''}-{view}.avi",
            )
        ]
    elif preset == "record-graphs":
        video_dir = os.environ["VIDEO_DIR"]
        scene_size = (180, 90)
        captions = False
        OFFSET_H = 229  # 228
        GRAPH_H = 445  # 426
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
        airliner_flight_path=airliner_fp,
        track_airplane_id=track_airplane_id,
        view=view,
        map_texture_fpath=(
            simulation_config.viz_config.map_view_config.map_texture_filename
            if view == "map-view"
            else simulation_config.viz_config.map_texture_filename
        ),
        zoompoints=zoompoints,
        scene_size=scene_size,
        theme=simulation_config.viz_config.theme,
        models_scale_factor=models_scale_factor,
        captions=captions,
        screen_recorders=screen_recorders,
    )
    environment.run()
    for screen_recorder in screen_recorders:
        screen_recorder.release()
    quit()


def make_uavs(
    simulation_config: SimulationConfig, fuel: Fuel, airliner_fp: AirlinerFlightPath
) -> Tuple[
    Dict[str, Dict[str, Dict[str, Uav]]], Dict[str, Dict[str, Dict[str, UavFlightPath]]]
]:
    uavs = {}
    uav_fps = {}
    for uav_airport_code, x in simulation_config.n_uavs_per_flyover_airport.items():
        airport_uav_idx = 0
        uavs[uav_airport_code] = {}
        uav_fps[uav_airport_code] = {}
        for service_side, n_uavs in x.dict().items():
            uavs[uav_airport_code][service_side] = {}
            uav_fps[uav_airport_code][service_side] = {}
            for service_side_uav_idx in range(n_uavs):
                # Instantiate the UAV:
                uavs_config = simulation_config.uavs_config
                uav = Uav(
                    id=f"{uav_airport_code}_UAV_{airport_uav_idx}",
                    airplane_spec=uavs_config.airplane_spec_name,
                    refueling_rate_kW=uavs_config.refueling_rate_kW,
                    initial_energy_level_pc=uavs_config.initial_energy_level_pc,
                    viz_model=uavs_config.viz_model_name,
                    payload_fuel=fuel,
                    initial_refueling_energy_level_pc=uavs_config.initial_refueling_energy_level_pc,
                )
                # Add the UAV to the `uavs` dict:
                uavs[uav_airport_code][service_side][uav.id] = uav

                refueling_rate_kW = min(
                    simulation_config.airliner_config.refueling_rate_kW,
                    simulation_config.uavs_config.refueling_rate_kW,
                )
                refueling_distance_km = (
                    uav.airplane_spec.cruise_speed_kmph
                    * uav.refueling_energy_capacity_MJ
                    / refueling_rate_kW
                    / MJ_PER_KWH
                )
                decreasing_towards_airport = (
                    service_side_uav_idx
                    if service_side == "from_airport"
                    else (n_uavs - service_side_uav_idx - 1)
                )
                uavs_fp_config = simulation_config.uavs_flight_path_config
                # Instantiate the UAV Flight Path:
                uav_fp = UavFlightPath(
                    home_airport=uav_airport_code,
                    takeoff_speed_kmph=uavs_fp_config.takeoff_speed_kmph,
                    takeoff_distance_km=uavs_fp_config.takeoff_distance_km,
                    takeoff_leveling_distance_km=uavs_fp_config.takeoff_leveling_distance_km,
                    rate_of_climb_mps=uavs_fp_config.rate_of_climb_mps,
                    climb_leveling_distance_km=uavs_fp_config.climb_leveling_distance_km,
                    cruise_altitude_km=(
                        uavs_fp_config.smallest_cruise_altitude_km
                        + uavs_fp_config.inter_uav_vertical_distance_km
                        * service_side_uav_idx
                    ),
                    cruise_speed_kmph=uav.airplane_spec.cruise_speed_kmph,
                    turning_radius_km=airliner_fp.turning_radius_km,
                    descent_leveling_distance_km=uavs_fp_config.descent_leveling_distance_km,
                    rate_of_descent_mps=uavs_fp_config.rate_of_descent_mps,
                    landing_leveling_distance_km=uavs_fp_config.landing_leveling_distance_km,
                    landing_distance_km=uavs_fp_config.landing_distance_km,
                    landing_speed_kmph=uavs_fp_config.landing_speed_kmph,

                    arc_radius_km=uavs_fp_config.arc_radius_km,
                    refueling_altitude_km=(
                        airliner_fp.cruise_altitude_km
                        + uavs_fp_config.airliner_uav_docking_distance_km
                    ),
                    refueling_distance_km=refueling_distance_km,
                    service_side=service_side,
                    undocking_distance_from_airport_km=(
                        uavs_fp_config.smallest_undocking_distance_from_airport_km
                        + (
                            refueling_distance_km
                            + uavs_fp_config.inter_uav_clearance_km
                        )
                        * decreasing_towards_airport
                    ),
                    airliner_clearance_speed_kmph=uavs_fp_config.airliner_clearance_speed_kmph,
                    airliner_clearance_distance_km=uavs_fp_config.airliner_clearance_distance_km,
                    airliner_clearance_altitude_km=(
                        uavs_fp_config.smallest_airliner_clearance_altitude_km
                        + uavs_fp_config.inter_uav_vertical_distance_km
                        * service_side_uav_idx
                    ),
                )
                # Add the UAV Flight Path to the `uav_fps` dict:
                uav_fps[uav_airport_code][service_side][uav.id] = uav_fp

                provision_uav_from_flight_path(
                    uav, service_side_uav_idx, n_uavs, uav_fp, airliner_fp
                )

                airport_uav_idx += 1

    return uavs, uav_fps


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
    subprocess.Popen(["google-chrome", "--guest", "--start-maximized"])
    run_scenario(
        simulation_config=SimulationConfig.from_yaml(args.config_dir),
        view=args.view,
        track_airplane_id=args.track_airplane_id,
        preset=args.preset,
    )
