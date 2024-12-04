import argparse
import datetime as dt
import os
import subprocess
from typing import Dict, Literal, Tuple

from src.airplanes_simulator import AirplanesSimulator
from src.feasibility_study.modeling_objects import Fuel
from src.modeling_objects import Airliner, AirplanesState, Uav, UavId
from src.three_d_sim.environments.airplanes_visualizer_environment import (
    AirplanesVisualizerEnvironment,
    ScreenRecorder,
    View,
)
from src.three_d_sim.flight_path_generation import (
    AirlinerFlightPath,
    AirportCode,
    ServiceSide,
    UavFlightPath,
    delay_uavs,
    generate_all_airliner_waypoints,
    generate_all_uav_waypoints,
    viz_airplane_paths,
    write_airplane_paths,
    write_airplane_tagged_waypoints,
)
from src.three_d_sim.simulation_config_schema import (
    SimulationConfig,
    ViewportSize,
    Zoompoint,
)
from src.utils.utils import MJ_PER_KWH, timedelta_to_minutes


def run_scenario(
    simulation_config: SimulationConfig,
    view: View,
    track_airplane_id: str,
    record: Literal["airplanes-viz", "graphs"],
) -> None:
    airliner_config = simulation_config.airliner_config
    airliner = Airliner(
        airplane_spec=airliner_config.airplane_spec,
        refueling_rate_kW=airliner_config.refueling_rate_kW,
        initial_energy_level_pc=airliner_config.initial_energy_level_pc,
        viz_model=airliner_config.viz_model_name,
    )
    airliner.flight_path = AirlinerFlightPath.from_configs(
        simulation_config.airliner_flight_path_config, airliner_config
    )

    uavs = make_uavs(
        simulation_config,
        fuel=airliner.airplane_spec.fuel,
        airliner_fp=airliner.flight_path,
    )

    waypoints = generate_all_airliner_waypoints(airliner.id, airliner.flight_path, uavs)
    airliner.location = waypoints.pop(0).LOCATION
    airliner.waypoints = waypoints

    flat_uavs = {
        k: {k2: v2 for x in v.values() for k2, v2 in x.items()} for k, v in uavs.items()
    }

    delay_uavs(flat_uavs, airliner)

    airplanes = [airliner] + [
        uav for uav_dict in flat_uavs.values() for uav in uav_dict.values()
    ]

    if view == "airplane-paths":
        if track_airplane_id is None:
            airplanes_to_track = airplanes
        else:
            airplanes_to_track = [airplanes[track_airplane_id]]
        write_airplane_paths(airplanes_to_track)
        write_airplane_tagged_waypoints(airplanes_to_track)
        if simulation_config.viz_enabled:
            viz_airplane_paths(airplanes_to_track)
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


def make_uavs(
    simulation_config: SimulationConfig, fuel: Fuel, airliner_fp: AirlinerFlightPath
) -> Dict[AirportCode, Dict[ServiceSide, Dict[UavId, Uav]]]:
    uavs = {}
    for uav_airport_code, x in simulation_config.n_uavs_per_flyover_airport.items():
        airport_uav_idx = 0
        uavs[uav_airport_code] = {}
        for service_side, n_uavs in x.dict().items():
            uavs[uav_airport_code][service_side] = {}
            for service_side_uav_idx in range(n_uavs):
                uav, uav_fp = make_uav(
                    simulation_config,
                    fuel,
                    airliner_fp,
                    uav_airport_code,
                    airport_uav_idx,
                    service_side,
                    n_uavs,
                    service_side_uav_idx,
                )
                # Add the UAV to the `uavs` dict:
                uavs[uav_airport_code][service_side][uav.id] = uav

                airport_uav_idx += 1

    return uavs


def make_uav(
    simulation_config: SimulationConfig,
    fuel: Fuel,
    airliner_fp: AirlinerFlightPath,
    uav_airport_code: AirportCode,
    airport_uav_idx: int,
    service_side: ServiceSide,
    n_uavs: int,
    service_side_uav_idx: int,
) -> Uav:
    uavs_config = simulation_config.uavs_config
    # Instantiate the UAV:
    uav = Uav(
        id=f"{uav_airport_code}_UAV_{airport_uav_idx}",
        airplane_spec=uavs_config.airplane_spec,
        refueling_rate_kW=uavs_config.refueling_rate_kW,
        initial_energy_level_pc=uavs_config.initial_energy_level_pc,
        viz_model=uavs_config.viz_model_name,
        payload_fuel=fuel,
        initial_refueling_energy_level_pc=uavs_config.initial_refueling_energy_level_pc,
    )

    refueling_rate_kW = min(
        simulation_config.airliner_config.refueling_rate_kW,
        simulation_config.uavs_config.refueling_rate_kW,
    )
    refueling_distance_km = (
        uavs_config.airplane_spec.cruise_speed_kmph
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
    uav.flight_path = UavFlightPath(
        home_airport=uav_airport_code,
        takeoff_speed_kmph=uavs_fp_config.takeoff_speed_kmph,
        takeoff_distance_km=uavs_fp_config.takeoff_distance_km,
        takeoff_leveling_distance_km=uavs_fp_config.takeoff_leveling_distance_km,
        rate_of_climb_mps=uavs_fp_config.rate_of_climb_mps,
        climb_leveling_distance_km=uavs_fp_config.climb_leveling_distance_km,
        cruise_altitude_km=(
            uavs_fp_config.smallest_cruise_altitude_km
            + uavs_fp_config.inter_uav_vertical_distance_km * service_side_uav_idx
        ),
        cruise_speed_kmph=uavs_config.airplane_spec.cruise_speed_kmph,
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
            + (refueling_distance_km + uavs_fp_config.inter_uav_clearance_km)
            * decreasing_towards_airport
        ),
        airliner_clearance_speed_kmph=uavs_fp_config.airliner_clearance_speed_kmph,
        airliner_clearance_distance_km=uavs_fp_config.airliner_clearance_distance_km,
        airliner_clearance_altitude_km=(
            uavs_fp_config.smallest_airliner_clearance_altitude_km
            + uavs_fp_config.inter_uav_vertical_distance_km * service_side_uav_idx
        ),
    )

    waypoints = generate_all_uav_waypoints(
        uav.id, service_side_uav_idx, n_uavs, uav.flight_path, airliner_fp
    )
    uav.location = waypoints.pop(0).LOCATION
    uav.waypoints = waypoints

    return uav


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
