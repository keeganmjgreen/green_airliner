import argparse
import datetime as dt
import subprocess

import cv2
import numpy as np

from src.emulators import EvTaxisEmulator as AirplanesEmulator
from src.environments import EnvironmentConfig
from src.modeling_objects import Airliner, EnvironmentState, Uav, ModelConfig
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
from src.utils.utils import J_PER_MJ, KWH_PER_MJ, MINUTES_PER_HOUR

from src.feasibility_study.study_params import BaseA320, Lh2FueledA320, at200, lh2_fuel

AIRLINER_ID = "Airliner"


def run_scenario(
    view: VIEW_TYPE, n_view_columns: int, track_airplane_id: str, preset: str
) -> None:
    start_timestamp = dt.datetime(2000, 1, 1, 0, 0)

    LH2_REFUELING_RATE_J_PER_MIN = 7e12 / 50
    charging_power_limit_kw = LH2_REFUELING_RATE_J_PER_MIN / J_PER_MJ * KWH_PER_MJ * MINUTES_PER_HOUR

    airliner = Airliner(
        ID=AIRLINER_ID,
        DISCHARGE_RATE_KWH_PER_KM=(
            BaseA320.energy_consumption_rate_MJph
            / BaseA320.cruise_speed_kmph
            * KWH_PER_MJ
        ),
        ENERGY_CAPACITY_KWH=(Lh2FueledA320.energy_capacity_MJ * KWH_PER_MJ),
        CHARGING_POWER_LIMIT_KW=charging_power_limit_kw,
        # ^ https://en.wikipedia.org/wiki/Megawatt_Charging_System
        DEFAULT_SPEED_KMPH=...,
        soc=1,
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
    AT200_FUEL_CONSUMPTION_RATE_L_PER_H = 184
    AT200_FUEL_CAPACITY_L = 1256
    # ^ https://www.aerospace.co.nz/files/dmfile/PAL%202016%20P-750%20XSTOL%20Brochure%20final.pdf
    AT200_CRUISE_SPEED_KMPH = 300
    JET_A1_FUEL_ENERGY_DENSITY_MJ_PER_KG = 43.15
    JET_A1_FUEL_DENSITY_KG_PER_L = 0.804
    uav_refueling_capacity_MJ = at200.energy_capacity_MJ(fuel=lh2_fuel)
    refueling_distance_km = (
        AT200_CRUISE_SPEED_KMPH
        / (LH2_REFUELING_RATE_J_PER_MIN * MINUTES_PER_HOUR)
        * (uav_refueling_capacity_MJ * J_PER_MJ)
    )
    undocking_distance_from_airport_km = 50
    inter_uav_clearance_km = 10
    uavs_per_airport = {
        "PIT": {"to-airport": 1, "from-airport": 1},
        "DEN": {"to-airport": 4, "from-airport": 3},
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
                    ID=f"{uav_airport_code}-UAV-{i}",
                    DISCHARGE_RATE_KWH_PER_KM=(
                        AT200_FUEL_CONSUMPTION_RATE_L_PER_H
                        / AT200_CRUISE_SPEED_KMPH
                        * JET_A1_FUEL_DENSITY_KG_PER_L
                        * JET_A1_FUEL_ENERGY_DENSITY_MJ_PER_KG
                        * KWH_PER_MJ
                    ),
                    ENERGY_CAPACITY_KWH=(
                        AT200_FUEL_CAPACITY_L
                        * JET_A1_FUEL_DENSITY_KG_PER_L
                        * JET_A1_FUEL_ENERGY_DENSITY_MJ_PER_KG
                        * KWH_PER_MJ
                    ),
                    CHARGING_POWER_LIMIT_KW=charging_power_limit_kw,
                    DEFAULT_SPEED_KMPH=...,
                    soc=1,
                    REFUELING_ENERGY_CAPACITY_KWH=(
                        uav_refueling_capacity_MJ * KWH_PER_MJ
                    ),
                    refueling_soc=1,
                    MODEL_CONFIG=ModelConfig(
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
                uavs[uav_airport_code][service_side][uav.ID] = uav

                AIRLINER_UAV_DOCKING_DISTANCE_KM = 0.0015

                uav_fp = UavFlightPath(
                    AIRPORT_CODES=[uav_airport_code],
                    TAKEOFF_SPEED_KMPH=100,
                    # ^ https://en.wikipedia.org/wiki/Takeoff
                    TAKEOFF_DISTANCE_KM=1,
                    TAKEOFF_LEVELING_DISTANCE_KM=0.1,
                    RATE_OF_CLIMB_MPS=35,
                    CLIMB_LEVELING_DISTANCE_KM=0.5,
                    CRUISE_ALTITUDE_KM=11.5,
                    CRUISE_SPEED_KMPH=AT200_CRUISE_SPEED_KMPH,
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
                        * ((n_uavs - j - 1) if service_side == "to-airport" else j)
                    ),
                    AIRLINER_CLEARANCE_SPEED_KMPH=200,
                    AIRLINER_CLEARANCE_DISTANCE_KM=10,
                    AIRLINER_CLEARANCE_ALTITUDE_KM=5,
                )
                uav_fps[uav_airport_code][service_side][uav.ID] = uav_fp

                provision_uav_from_flight_path(uav, uav_fp, airliner_fp)

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
        START_STATE=EnvironmentState(
            evs_state={airplane.ID: airplane for airplane in airplanes},
        ),
    )

    if view != "map-view":
        assert track_airplane_id is not None
        models_scale_factor = 1
        if track_airplane_id == "Airliner":
            zoom = [
                (0, 5),
                (3, 0.05),
                (51.3, 0.05),
                (51.9, 5),
                (52, 5),
                (52.6, 0.8),
                (57, 0.1),
                (60, 0.07),
                (63, 0.1),
                (71.6, 0.8),
                (72.2, 5),
                (72.8, 0.1),
                (75, 0.02),
                (95, 0.001),
                (250, 0.0005),
                (260, 0.02),
                (262.8, 0.05),
                (263.4, 5),
                (264, 0.3),
                (280, 0.07),
                (285, 0.3),
                (295, 0.5),
                (298, 0.02),
                (320, 0.001),
                (405, 0.001),
                (410, 0.05),
                (414, 0.5),
                (415, 5),
            ]
        elif track_airplane_id == "PIT-UAV-0":
            zoom = [
                (0, 20),
                (25, 20),
                (30, 5),
                (51.5, 5),
                (51.7, 20),
                (55, 1),
                (60, 1),
                (63, 5),
                (65, 20),
                (100, 20),
            ]
        elif track_airplane_id == "PIT-UAV-1":
            offset = 20.3
            zoom = [
                (offset + 0, 20),
                (offset + 25, 20),
                (offset + 30, 5),
                (offset + 51.5, 5),
                (offset + 51.7, 20),
                (offset + 55, 1),
                (offset + 60, 1),
                (offset + 63, 5),
                (offset + 65, 20),
                (100, 20),
            ]
        else:
            zoom = [(0, 20), (415, 20)]
    else:
        models_scale_factor = 20000
        zoom = [(0, 10), (415, 10)]

    scene_size = (1800, 900)
    captions = True
    if preset == "record-airplanes-viz":
        screen_recorders = [
            ScreenRecorder(
                origin=(8, 128),
                size=scene_size,
                fname=f"/home/keegan_green/Downloads/electric_airliner_video/electric_airliner_video-{track_airplane_id or ''}-{view}.avi",
            )
        ]
    elif preset == "record-graphs":
        scene_size = (180, 90)
        captions = False
        screen_recorders = [
            ScreenRecorder(
                origin=(8, 218),
                size=(640, 426),
                fname="/home/keegan_green/Downloads/electric_airliner_video/electric_airliner_video-Airliner-soc-graph.avi",
            ),
            ScreenRecorder(
                origin=(8, 218 + 426),
                size=(640, 426),
                fname="/home/keegan_green/Downloads/electric_airliner_video/electric_airliner_video-Airliner-speed-graph.avi",
            ),
        ]
    else:
        screen_recorders = []

    environment = AirplanesVisualizerEnvironment(
        ENVIRONMENT_CONFIG=EnvironmentConfig(
            TIME_STEP=[
                (0, 1),
                (5, 1),
                (10, 30),
                (40, 30),
                (50, 1),
                (62, 3),
                (74, 1),
                (84, 50),
                (250, 50),
                (260, 1),
                (264, 2),
                (285, 2),
                (320, 30),
                (405, 30),
                (410, 1),
                (415, 1),
            ],
            DELAY_TIME_STEP=dt.timedelta(seconds=0.04),
            START_TIMESTAMP=start_timestamp,
            SKIP_TIMEDELTA=dt.timedelta(minutes=0),
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
    cv2.destroyAllWindows()
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
