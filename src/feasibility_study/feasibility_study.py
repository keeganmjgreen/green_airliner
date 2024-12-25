"""
Todos:
    Taxiing, takeoff, landing, and taxiing again.
    Reduced fuel capacity.
    Reduced fuel energy density (and different fuel density).
    With vs. without mid-air refueling.
"""

import matplotlib.pyplot as plt

from src import specs
from src.feasibility_study.study_runner import run_study
from src.utils.utils import MJ_PER_GJ

if __name__ == "__main__":
    reserve_energy_thres_MJ = 100e3
    for study_label, (airliner_class, n_refuels_by_waypoint) in {
        "Jet-fueled A320": (specs.JetFueledA320, {}),
        "LH2-fueled A320": (specs.Lh2FueledA320, {"PIT": 0, "DEN": 0}),
        "LH2-fueled A320 with refueling": (
            specs.Lh2FueledA320,
            {"PIT": "auto", "DEN": "auto"},
        ),
        "Lion-fueled A320": (specs.LionFueledA320, {"PIT": 0, "DEN": 0}),
        "Lion-fueled A320 with refueling": (
            specs.LionFueledA320,
            {"PIT": "auto", "DEN": "auto"},
        ),
    }.items():
        airliner = airliner_class(reserve_energy_thres_MJ)
        airliner.energy_quantity_MJ = airliner.energy_capacity_MJ
        results_df = run_study(
            study_label,
            airliner=airliner,
            uav=specs.At200,
            origin_airport="JFK",
            destination_airport="LAX",
            n_refuels_by_waypoint=n_refuels_by_waypoint,
        )
    plt.xlim((0, None))
    plt.xlabel("Time Into Flight (Hours)")
    plt.ylabel("Remaining Energy (GJ)")
    plt.axhline(y=0, color="black")
    plt.axhline(
        y=reserve_energy_thres_MJ / MJ_PER_GJ,
        color="gray",
        label="Reserve Energy Threshold",
    )
    plt.legend()
    plt.savefig("docs/5_feasibility_studies/feasibility_study.svg")
    plt.savefig("docs/5_feasibility_studies/feasibility_study.png", dpi=300)
