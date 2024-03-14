from copy import deepcopy
from typing import Dict, List, Literal, Optional, Union

import matplotlib.pyplot as plt
import pandas as pd

from src.feasibility_study.study_params import (
    DISTANCE_KM_LOOKUP,
    MJ_PER_GJ,
    BaseAirliner,
    Uav,
)


def run_study(
    study_label: str,
    airliner: BaseAirliner,
    uav: Uav,
    waypoints: List[str],
    n_refuels_by_waypoint: Optional[Dict[str, Union[int, Literal["auto"]]]] = {},
) -> pd.DataFrame:
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
                            energy_quantity_MJ=uav.energy_capacity_MJ(
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
                        energy_quantity_MJ=uav.energy_capacity_MJ(fuel=airliner.fuel)
                    )
                    update_ser()

    print(f"\n{study_label}:")
    print(ser)
    plot_ser = (
        (ser / MJ_PER_GJ)
        .rename("energy_GJ")
        .reset_index()
        .set_index("time_into_flight_h")["energy_GJ"]
    )
    plt.plot(plot_ser, "-o", label=study_label)
    return ser
