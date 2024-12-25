"""
Todos:
    Taxiing, takeoff, landing, and taxiing again.
    Reduced fuel capacity.
    Reduced fuel energy density (and different fuel density).
    With vs. without mid-air refueling.
"""

import plotly.graph_objects as go

from src import specs
from src.feasibility_study.study_runner import run_study
from src.utils.utils import MJ_PER_GJ

if __name__ == "__main__":
    fig = go.Figure()
    reserve_energy_thres_MJ = 100e3
    fig.add_hline(
        y=(reserve_energy_thres_MJ / MJ_PER_GJ),
        annotation_text="Reserve Energy Threshold",
    )
    for study_label, (airliner_class, n_refuels_by_waypoint) in {
        "Jet-A1-fueled A320": (specs.JetFueledA320, {}),
        "LH₂-fueled A320": (specs.Lh2FueledA320, {"PIT": 0, "DEN": 0}),
        "LH₂-fueled A320 with refueling": (
            specs.Lh2FueledA320,
            {"PIT": "auto", "DEN": "auto"},
        ),
        "Li-ion-fueled A320": (specs.LionFueledA320, {"PIT": 0, "DEN": 0}),
        "Li-ion-fueled A320 with refueling": (
            specs.LionFueledA320,
            {"PIT": "auto", "DEN": "auto"},
        ),
    }.items():
        airliner = airliner_class(reserve_energy_thres_MJ)
        airliner.energy_quantity_MJ = airliner.energy_capacity_MJ
        results_df = run_study(
            airliner=airliner,
            uav=specs.At200,
            origin_airport="JFK",
            destination_airport="LAX",
            n_refuels_by_waypoint=n_refuels_by_waypoint,
        )
        print(f"\n{study_label}:")
        print(results_df)
        fig.add_scatter(
            x=results_df["time_into_flight_h"].round(2),
            y=(results_df["energy_MJ"] / MJ_PER_GJ).round(3),
            mode="lines+markers",
            name=study_label,
        )
    fig.update_layout(
        xaxis_range=[0, 5],
        xaxis_title="Time Into Flight (Hours)",
        yaxis_title="Remaining Energy (GJ)",
        yaxis_tickformat="3.s",
        title="Feasibility Studies with Different Energy Storage Media",
        font_color="black",
        font_family="FreeSans",
        plot_bgcolor="#f8f8f8",
        margin=dict(l=20, r=20, b=20, t=50),
    )
    fig.write_html("docs/_static/feasibility_study.html")
    fig.write_image("docs/5_feasibility_studies/feasibility_study.svg")
    fig.write_image("docs/5_feasibility_studies/feasibility_study.png")
