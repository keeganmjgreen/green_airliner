from typing import Dict, Literal, Optional, Union

import pandas as pd

from src import specs
from src.feasibility_study.modeling_objects import BaseAirliner, Uav
from src.feasibility_study.study_runner import run_study
from src.modeling_objects import Location, get_all_airport_locations

ALL_AIRPORT_LOCATIONS = get_all_airport_locations()


def generate_optimized_flight_plan(
    airliner: BaseAirliner, uav: Uav, origin_airport: str, destination_airport: str
):
    def _run_study(
        n_refuels_by_waypoint: Optional[Dict[str, Union[int, Literal["auto"]]]] = {}
    ) -> pd.DataFrame:
        waypoints = [
            origin_airport,
            *n_refuels_by_waypoint.keys(),
            destination_airport,
        ]  # TODO remove
        study_label = " - ".join(waypoints)
        results_df = run_study(
            study_label,
            airliner,
            uav,
            origin_airport,
            destination_airport,
            n_refuels_by_waypoint,
        )
        return results_df

    results_df = _run_study(n_refuels_by_waypoint={})
    for i in range(1, len(results_df)):
        prev_airport = results_df.loc[i - 1]["waypoint"]
        next_airport = results_df.loc[i]["waypoint"]
        if results_df.loc[i]["energy_MJ"] < airliner.reserve_energy_thres_MJ:
            range_km = airliner.calculate_range_km(results_df.loc[i - 1]["energy_MJ"])
            potential_flyover_airports = [
                potential_flyover_airport
                for potential_flyover_airport in ALL_AIRPORT_LOCATIONS
                if Location.direct_distance_km_between(
                    ALL_AIRPORT_LOCATIONS[prev_airport],
                    potential_flyover_airport,
                )
                <= range_km
            ]
            ...  # TODO find airport closest to line [waypoint-1, waypoint]


if __name__ == "__main__":
    airliner = specs.Lh2FueledA320(reserve_energy_thres_MJ=100e3)
    airliner.energy_quantity_MJ = airliner.energy_capacity_MJ
    generate_optimized_flight_plan(
        airliner=airliner,
        uav=specs.At200,
        origin_airport="JFK",
        destination_airport="LAX",
    )
