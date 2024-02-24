import argparse
import datetime as dt

import numpy as np

from src.emulators import EvTaxisEmulator as AirplanesEmulator
from src.environments import EnvironmentConfig
from src.modeling_objects import Airliner, EnvironmentState, Uav, ModelConfig
from src.projects.electric_airliner.airplanes_visualizer_environment import (
    VIEW_TYPE,
    AirplanesVisualizerEnvironment,
)
from src.projects.electric_airliner.flight_path_generation import (
    AirlinerFlightPath,
    UavFlightPath,
    delay_uavs,
    provision_airliner_from_flight_path,
    provision_uav_from_flight_path,
    viz_airplane_paths,
)
from src.utils.utils import J_PER_MJ, KWH_PER_MJ, MINUTES_PER_HOUR

from electric_airline.src.study_params import BaseA320, Lh2FueledA320, at200, lh2_fuel

AIRLINER_ID = "Airliner"


def run_scenario(view: VIEW_TYPE, n_view_columns: int, track_airplane_id: str) -> None:
    start_timestamp = dt.datetime(2000, 1, 1, 0, 0)

    scale_factor = 1

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
        "PIT": {"to-airport": 2, "from-airport": 1},
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

    environment = AirplanesVisualizerEnvironment(
        ENVIRONMENT_CONFIG=EnvironmentConfig(
            TIME_STEP=dt.timedelta(seconds=6),
            DELAY_TIME_STEP=dt.timedelta(seconds=0.04),
            START_TIMESTAMP=start_timestamp,
            SKIP_TIMEDELTA=dt.timedelta(minutes=40),
            END_TIMESTAMP=None,
        ),
        ev_taxis_emulator_or_interface=airplanes_emulator,
        AIRLINER_FLIGHT_PATH=airliner_fp,
        TRACK_AIRPLANE_ID=track_airplane_id,
        VIEW=view,
        N_VIEW_COLUMNS=n_view_columns,
        MODELS_SCALE_FACTOR=scale_factor,
    )
    environment.run()


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--view", dest="view")
    parser.add_argument("--n-view-columns", dest="n_view_columns", default=1)
    parser.add_argument(
        "--track-airplane-id", dest="track_airplane_id", default=AIRLINER_ID
    )
    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_cli_args()
    run_scenario(
        view=args.view,
        n_view_columns=int(args.n_view_columns),
        track_airplane_id=args.track_airplane_id,
    )
