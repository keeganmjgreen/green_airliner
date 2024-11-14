from copy import deepcopy
from typing import Dict, Literal, Optional, Union

import matplotlib.pyplot as plt
import pandas as pd

from src.feasibility_study.modeling_objects import BaseAirliner, Uav
from src.specs import DISTANCE_KM_LOOKUP
from src.utils.utils import MJ_PER_GJ


def run_study(
    study_label: str,
    airliner: BaseAirliner,
    uav: Uav,
    origin_airport: str,
    destination_airport: str,
    n_refuels_by_waypoint: Optional[Dict[str, Union[int, Literal["auto"]]]] = {},
) -> pd.DataFrame:
    waypoints = [
        origin_airport,
        *n_refuels_by_waypoint.keys(),
        destination_airport,
    ]

    ser = pd.DataFrame(
        columns=[
            "index",
            "time_into_flight_h",
            "waypoint",
            "energy_MJ",
        ]
    ).set_index(["index", "time_into_flight_h", "waypoint"])["energy_MJ"]

    ser.loc[(len(ser), airliner.time_into_flight_h, waypoints[0])] = (
        airliner.energy_quantity_MJ
    )

    for i in range(len(waypoints) - 1):
        distance_km = DISTANCE_KM_LOOKUP[waypoints[i], waypoints[i + 1]]
        airliner.fly(distance_km)

        ser.loc[(len(ser), airliner.time_into_flight_h, waypoints[i + 1])] = (
            airliner.energy_quantity_MJ
        )

        def update_ser():
            ser.loc[len(ser), airliner.time_into_flight_h, waypoints[i + 1]] = (
                airliner.energy_quantity_MJ
            )

        if i < len(waypoints) - 2:
            if n_refuels_by_waypoint[waypoints[i + 1]] == "auto":
                while True:
                    tmp_airliner = deepcopy(airliner)
                    tmp_airliner.fly(
                        distance_km=DISTANCE_KM_LOOKUP[
                            waypoints[i + 1], waypoints[i + 2]
                        ]
                    )
                    if (
                        tmp_airliner.energy_quantity_MJ
                        < tmp_airliner.reserve_energy_thres_MJ
                        and airliner.energy_quantity_MJ < airliner.energy_capacity_MJ
                    ):
                        airliner.refuel(
                            energy_quantity_MJ=uav.refueling_energy_capacity_MJ(
                                fuel=airliner.fuel
                            )
                        )
                        update_ser()
                    else:
                        break
            else:
                n_refuels = n_refuels_by_waypoint[waypoints[i + 1]]
                for j in range(n_refuels):
                    airliner.refuel(
                        energy_quantity_MJ=uav.refueling_energy_capacity_MJ(fuel=airliner.fuel)
                    )
                    update_ser()

    results_df = ser.to_frame().set_index("index")

    print(f"\n{study_label}:")
    print(results_df)

    plot_ser = (
        (ser / MJ_PER_GJ)
        .rename("energy_GJ")
        .reset_index()
        .set_index("time_into_flight_h")["energy_GJ"]
    )
    plt.plot(plot_ser, "-o", label=study_label)

    return results_df
