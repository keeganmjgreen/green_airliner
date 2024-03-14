"""
Todos:
    Taxiing, takeoff, landing, and taxiing again.
    Reduced fuel capacity.
    Reduced fuel energy density (and different fuel density).
    With vs. without mid-air refueling.
"""

import matplotlib.pyplot as plt

from src.feasibility_study.study_params import MJ_PER_GJ, JetFueledA320, Lh2FueledA320, LionFueledA320, at200
from src.feasibility_study.study_runner import run_study


if __name__ == "__main__":
    reserve_energy_thres_MJ = 100e3
    for study_label, (airliner_class, n_refuels_per_waypoint) in {
        "Jet-fueled A320": (JetFueledA320, {}),
        "LH2-fueled A320": (Lh2FueledA320, {"PIT": 0, "DEN": 0}),
        "LH2-fueled A320 with refueling": (Lh2FueledA320, {"PIT": "auto", "DEN": "auto"}),
        "Lion-fueled A320": (LionFueledA320, {"PIT": 0, "DEN": 0}),
        "Lion-fueled A320 with refueling": (LionFueledA320, {"PIT": "auto", "DEN": "auto"}),
    }.items():
        airliner = airliner_class(reserve_energy_thres_MJ)
        airliner.energy_quantity_MJ = airliner.energy_capacity_MJ
        results_df = run_study(
            study_label,
            airliner=airliner,
            uav=at200,
            waypoints=[
                "JFK",
                *n_refuels_per_waypoint.keys(),
                "LAX",
            ],
            n_refuels_by_waypoint=n_refuels_per_waypoint,
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
    plt.savefig("tmp/feasibility_study.svg")
    plt.savefig("tmp/feasibility_study.png", dpi=300)
    plt.show()
