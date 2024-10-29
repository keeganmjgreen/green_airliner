import argparse
import datetime as dt
import subprocess

import numpy as np

from src.emulators import EvTaxisEmulator as AirplanesEmulator
from src.environments import EnvironmentConfig
from src.modeling_objects import Airliner, AirplanesState, Uav, ModelConfig
from src.three_d_sim.airplanes_visualizer_environment import (
    VIEW_TYPE,
    AirplanesVisualizerEnvironment,
    ScreenRecorder,
)
from src.three_d_sim.flight_path_generation import (
    AirlinerFlightPath,
    UavFlightPath,
    delay_uavs,
    provision_airliner_from_flight_path,
    provision_uav_from_flight_path,
    viz_airplane_paths,
)
from src.utils.utils import J_PER_MJ, J_PER_WH, MINUTES_PER_HOUR, SECONDS_PER_HOUR, _getenv, timedelta_to_minutes

from src.feasibility_study.study_params import BaseA320, Lh2FueledA320, at200, lh2_fuel


def run_scenario(
    view: VIEW_TYPE, n_view_columns: int, track_airplane_id: str, preset: str
) -> None:
    start_timestamp = dt.datetime(2000, 1, 1, 0, 0)

    LH2_REFUELING_RATE_J_PER_MIN = 7e12 / 50
    refueling_rate_kW = LH2_REFUELING_RATE_J_PER_MIN / J_PER_WH * MINUTES_PER_HOUR

    airliner = Airliner(
        energy_consumption_rate_MJ_per_km=BaseA320.energy_consumption_rate_MJ_per_km,
        energy_capacity_MJ=Lh2FueledA320.energy_capacity_MJ,
        refueling_rate_kW=refueling_rate_kW,
        energy_level_pc=100.0,
        MODEL_CONFIG=ModelConfig(
            MODEL_SUBPATH="airliner/airbus-a320--1/Airbus_A320__Before_Scale_Up_-meshlabjs-simplified.obj",
            ROTATION_MATRIX=np.array(
                [
                    [0, 1, 0],
                    [0, 0, 1],
                    [1, 0, 0],
                ]
            ),
            LENGTH_M=37.57,
            # ^ https://aircraft.airbus.com/en/aircraft/a320-the-most-successful-aircraft-family-ever/a320ceo
        ),
    )
    airliner_fp = AirlinerFlightPath(
        AIRPORT_CODES=["JFK", "PIT", "DEN", "LAX"],
        TAKEOFF_SPEED_KMPH=np.mean([240, 285]),
        # ^ https://en.wikipedia.org/wiki/Takeoff
        TAKEOFF_DISTANCE_KM=1,
        TAKEOFF_LEVELING_DISTANCE_KM=0.1,
        RATE_OF_CLIMB_MPS=70,
        CLIMB_LEVELING_DISTANCE_KM=10,
        CRUISE_ALTITUDE_KM=np.mean([9.4, 11.6]),
        # ^ https://en.wikipedia.org/wiki/Cruise_%28aeronautics%29
        CRUISE_SPEED_KMPH=BaseA320.cruise_speed_kmph,
        TURNING_RADIUS_KM=50,
        DESCENT_LEVELING_DISTANCE_KM=10,
        RATE_OF_DESCENT_MPS=100,
        LANDING_LEVELING_DISTANCE_KM=0.1,
        LANDING_DISTANCE_KM=1,
        LANDING_SPEED_KMPH=200,
        SPEED_CHANGE_DISTANCE_KM=50,
    )

    uavs = {}
    uav_fps = {}
    uav_refueling_energy_capacity_MJ = at200.refueling_energy_capacity_MJ(fuel=lh2_fuel)
    refueling_distance_km = (
        at200.cruise_speed_kmph
        / (LH2_REFUELING_RATE_J_PER_MIN * MINUTES_PER_HOUR)
        * (uav_refueling_energy_capacity_MJ * J_PER_MJ)
    )
    undocking_distance_from_airport_km = 50
    inter_uav_clearance_km = 15
    inter_uav_vertical_dist_km = 1
    uavs_per_airport = {
        "PIT": {"to-airport": 1, "from-airport": 1},
        "DEN": {"to-airport": 3, "from-airport": 2},
    }
    for uav_airport_code, x in uavs_per_airport.items():
        i = 0
        uavs[uav_airport_code] = {}
        uav_fps[uav_airport_code] = {}
        for service_side, n_uavs in x.items():
            uavs[uav_airport_code][service_side] = {}
            uav_fps[uav_airport_code][service_side] = {}
            for j in range(n_uavs):
                uav = Uav(
                    id=f"{uav_airport_code}-UAV-{i}",
                    energy_consumption_rate_MJ_per_km=at200.energy_consumption_rate_MJ_per_km,
                    energy_capacity_MJ=at200.energy_capacity_MJ,
                    refueling_rate_kW=refueling_rate_kW,
                    energy_level_pc=100.0,
                    refueling_energy_capacity_MJ=uav_refueling_energy_capacity_MJ,
                    refueling_energy_level_pc=1,
                    model_config=ModelConfig(
                        MODEL_SUBPATH="uav/cessna-208-1.snapshot.2/Cessna_208-meshlab.obj",
                        ROTATION_MATRIX=np.array(
                            [
                                [-1, 0, 0],
                                [0, 1, 0],
                                [0, 0, 1],
                            ]
                        ),
                        LENGTH_M=11.45,
                        # ^ https://cessna.txtav.com/en/turboprop/caravan
                        #     https://cessna.txtav.com/-/media/cessna/files/caravan/caravan/caravan_short_productcard.ashx
                    ),
                )
                uavs[uav_airport_code][service_side][uav.id] = uav

                AIRLINER_UAV_DOCKING_DISTANCE_KM = 0.0015

                decreasing_towards_airport = ((n_uavs - j - 1) if service_side == "to-airport" else j)

                uav_fp = UavFlightPath(
                    AIRPORT_CODES=[uav_airport_code],
                    TAKEOFF_SPEED_KMPH=100,
                    # ^ https://en.wikipedia.org/wiki/Takeoff
                    TAKEOFF_DISTANCE_KM=1,
                    TAKEOFF_LEVELING_DISTANCE_KM=0.1,
                    RATE_OF_CLIMB_MPS=35,
                    CLIMB_LEVELING_DISTANCE_KM=0.5,
                    CRUISE_ALTITUDE_KM=(11.5 + inter_uav_vertical_dist_km * j),
                    CRUISE_SPEED_KMPH=at200.cruise_speed_kmph,
                    TURNING_RADIUS_KM=airliner_fp.TURNING_RADIUS_KM,
                    DESCENT_LEVELING_DISTANCE_KM=0.5,
                    RATE_OF_DESCENT_MPS=50,
                    LANDING_LEVELING_DISTANCE_KM=0.1,
                    LANDING_DISTANCE_KM=1,
                    LANDING_SPEED_KMPH=200,
                    ARC_RADIUS_KM=1,
                    REFUELING_ALTITUDE_KM=(
                        airliner_fp.CRUISE_ALTITUDE_KM
                        + AIRLINER_UAV_DOCKING_DISTANCE_KM
                    ),
                    REFUELING_DISTANCE_KM=refueling_distance_km,
                    SERVICE_SIDE=service_side,
                    UNDOCKING_DISTANCE_FROM_AIRPORT_KM=(
                        undocking_distance_from_airport_km
                        + (refueling_distance_km + inter_uav_clearance_km)
                        * decreasing_towards_airport
                    ),
                    AIRLINER_CLEARANCE_SPEED_KMPH=200,
                    AIRLINER_CLEARANCE_DISTANCE_KM=5,
                    AIRLINER_CLEARANCE_ALTITUDE_KM=(5 + inter_uav_vertical_dist_km * j),
                )
                uav_fps[uav_airport_code][service_side][uav.id] = uav_fp

                provision_uav_from_flight_path(uav, j, n_uavs, uav_fp, airliner_fp)

                i += 1

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

    airplanes_emulator = AirplanesEmulator(
        START_TIMESTAMP=start_timestamp,
        START_STATE=AirplanesState(
            airplanes={airplane.id: airplane for airplane in airplanes},
        ),
    )

    skip_timedelta = dt.timedelta(minutes=0)
    d_airliner = airliner.get_elapsed_time_at_tagged_waypoints()
    d_airliner = {k: timedelta_to_minutes(v) for k, v in d_airliner.items()}
    airliner_curve_over_pit_midpoint = (
        d_airliner["Airliner-curve-over-PIT-start-point"]
        + d_airliner["Airliner-curve-over-PIT-end-point"]
    ) / 2
    airliner_curve_over_den_midpoint = (
       d_airliner["Airliner-curve-over-DEN-start-point"]
       + d_airliner["Airliner-curve-over-DEN-end-point"]
    ) / 2
    if view != "map-view":
        assert track_airplane_id is not None
        models_scale_factor = 1
        if track_airplane_id == "Airliner":
            d = d_airliner
            zoom = [
                (0, 5),
                (d["Airliner-takeoff-point"], 0.5),
                (d["Airliner-ascended-point"], 0.5),
                (d["Airliner-ascended-point"] + 0.5, 0.04),

                (d["PIT-UAV-0-on-airliner-docking-point"] - 1, 0.02),
                (d["PIT-UAV-0-on-airliner-docking-point"] - 0.3, 0.5),
                (d["PIT-UAV-0-on-airliner-undocking-point"] - 0.1, 10),
                (d["PIT-UAV-0-on-airliner-undocking-point"] + 0.5, 0.5),
                (airliner_curve_over_pit_midpoint - 5, 0.1),
                (airliner_curve_over_pit_midpoint, 0.05),
                (airliner_curve_over_pit_midpoint + 5, 0.1),
                (d["PIT-UAV-1-on-airliner-docking-point"] - 0.3, 0.5),
                (d["PIT-UAV-1-on-airliner-undocking-point"] - 0.1, 10),
                (d["PIT-UAV-1-on-airliner-undocking-point"] + 0.5, 0.5),
                (d["PIT-UAV-1-on-airliner-undocking-point"] + 2, 0.02),
                (d["PIT-UAV-1-on-airliner-undocking-point"] + 20, 0.005),

                (d["DEN-UAV-0-on-airliner-docking-point"] - 5, 0.004),
                (d["DEN-UAV-0-on-airliner-docking-point"] - 1, 0.02),
                (d["DEN-UAV-0-on-airliner-docking-point"] - 0.3, 0.5),
                (d["DEN-UAV-0-on-airliner-undocking-point"] - 0.1, 10),
                (d["DEN-UAV-0-on-airliner-undocking-point"] + 0.5, 0.5),
                (airliner_curve_over_den_midpoint, 0.05),
                (d["DEN-UAV-3-on-airliner-docking-point"], 0.5),
                (d["DEN-UAV-4-on-airliner-undocking-point"], 0.1),
                (d["DEN-UAV-4-on-airliner-undocking-point"] + 1, 0.02),
                (d["DEN-UAV-4-on-airliner-undocking-point"] + 25, 0.002),

                (d["Airliner-descent-point"] - 50, 0.002),
                (d["Airliner-descent-point"], 0.04),
                (d["Airliner-landing-point"], 0.04),
                (d["Airliner-landed-point"] + 1, 0.5),
                (d["Airliner-landed-point"] + 5, 5),
            ]
        else:
            uav_id = track_airplane_id
            uav_airport_code = track_airplane_id[:3]
            service_side = "to-airport" if uav_id in uavs[uav_airport_code]["to-airport"] else "from-airport"
            d = uavs[uav_airport_code][service_side][uav_id].get_elapsed_time_at_tagged_waypoints()
            d = {k.removeprefix(f"{track_airplane_id}-").removesuffix("-point"): timedelta_to_minutes(v) for k, v in d.items()}

            airport_last_uav_id = list(uavs[uav_airport_code]["from-airport"].keys())[-1]
            airport_last_uav_td = uavs[uav_airport_code]["from-airport"][airport_last_uav_id].get_elapsed_time_at_tagged_waypoints()[f"{airport_last_uav_id}-landed-point"]

            LANDED_UAVS_WAITING_TIME_MINS = 30
            CORRECTION_MINS = (60 + 47) / SECONDS_PER_HOUR

            if service_side == "to-airport":
                zoom = [
                    (0, 50),
                    (d["takeoff"] - 2, 50),
                    (d["takeoff"] - 1, 1),
                    (d["ascended"], 1),
                    (d["ascended"] + 1, 5),
                    (d["arc-start"], 5),
                    (d["descent-to-airliner"], 0.5),
                    (d["on-airliner-docking"], 5),
                    (d["on-airliner-docking"] + 0.1, 50),
                    (d["on-airliner-undocking"] - 0.1, 50),
                    (d["on-airliner-undocking"], 5),
                    (d["ascended-from-airliner"], 0.5),
                    (d["descent"], 0.5),
                    (d["landed"], 5),
                    (d["landed"] + 2, 50),
                    (timedelta_to_minutes(airport_last_uav_td) + LANDED_UAVS_WAITING_TIME_MINS, 50),
                ]
            else:
                zoom = [
                    (0, 50),
                    (d["takeoff"] - 2, 50),
                    (d["takeoff"] - 1, 1),
                    (d["ascended"], 1),
                    (d["ascended"] + 1, 5),
                    (d["descent-to-airliner"], 0.5),
                    (d["on-airliner-docking"], 5),
                    (d["on-airliner-docking"] + 0.1, 50),
                    (d["on-airliner-undocking"] - 0.1, 50),
                    (d["on-airliner-undocking"], 5),
                    (d["ascended-from-airliner"], 0.5),
                    (d["arc-end"], 0.25),
                    (d["landed"], 5),
                    (d["landed"] + 2, 50),
                    (timedelta_to_minutes(airport_last_uav_td) + LANDED_UAVS_WAITING_TIME_MINS, 50),
                ]
            if uav_airport_code != "PIT":
                last_pit_uav_id = list(uavs["PIT"]["from-airport"].keys())[-1]
                skip_timedelta = uavs["PIT"]["from-airport"][last_pit_uav_id].get_elapsed_time_at_tagged_waypoints()[f"{last_pit_uav_id}-landed-point"] + dt.timedelta(minutes=(LANDED_UAVS_WAITING_TIME_MINS - CORRECTION_MINS))
                # first_den_uav_id = list(uavs["DEN"]["to-airport"].keys())[0]
                # skip_timedelta = uavs["DEN"]["to-airport"][first_den_uav_id].get_elapsed_time_at_tagged_waypoints()[f"{first_den_uav_id}-first-point"] - dt.timedelta(minutes=2)
    else:
        models_scale_factor = 20000
        zoom = [(0, 10), (415, 10)]

    scene_size = (1800, 900)
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

    environment = AirplanesVisualizerEnvironment(
        ENVIRONMENT_CONFIG=EnvironmentConfig(
            TIME_STEP=[
                (0, 1),
                (d_airliner["Airliner-ascended-point"], 1),
                (d_airliner["Airliner-ascended-point"] + 5, 30),

                (d_airliner["PIT-UAV-0-on-airliner-docking-point"] - 5, 30),
                (d_airliner["PIT-UAV-0-on-airliner-docking-point"] - 1.5, 1),
                (d_airliner["PIT-UAV-0-on-airliner-undocking-point"] + 1.5, 1),
                (airliner_curve_over_pit_midpoint, 3),
                (d_airliner["PIT-UAV-1-on-airliner-docking-point"] - 1.5, 2),
                (d_airliner["PIT-UAV-1-on-airliner-undocking-point"] + 1.5, 2),
                (d_airliner["PIT-UAV-1-on-airliner-undocking-point"] + 10, 50),

                (d_airliner["DEN-UAV-0-on-airliner-docking-point"] - 10, 50),
                (d_airliner["DEN-UAV-0-on-airliner-docking-point"] - 1.5, 1),
                (d_airliner["DEN-UAV-0-on-airliner-undocking-point"] + 1.5, 1),
                (airliner_curve_over_den_midpoint, 3),
                (airliner_curve_over_den_midpoint + 40, 30),

                (d_airliner["Airliner-descent-point"] - 5, 30),
                (d_airliner["Airliner-descent-point"], 2),
                (d_airliner["Airliner-landed-point"] + 5, 2),
            ],
            DELAY_TIME_STEP=dt.timedelta(seconds=0.04),
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
        N_VIEW_COLUMNS=n_view_columns,
        MODELS_SCALE_FACTOR=models_scale_factor,
        CAPTIONS=captions,
        SCREEN_RECORDERS=screen_recorders,
    )
    environment.run()
    for screen_recorder in screen_recorders:
        screen_recorder.release()
    quit()


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view")
    parser.add_argument("--n-view-columns", default=1)
    parser.add_argument("--track-airplane-id", default=None)
    parser.add_argument("--preset", default=None)
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_cli_args()
    subprocess.Popen(["google-chrome", "--guest", "--start-maximized"])
    run_scenario(
        view=args.view,
        n_view_columns=int(args.n_view_columns),
        track_airplane_id=args.track_airplane_id,
        preset=args.preset,
    )
