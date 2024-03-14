import datetime as dt

import numpy as np

from src.feasibility_study.modeling_objects import BaseAirliner, Fuel, Propulsion, Uav

MJ_PER_GJ = 1000

L_PER_CUBIC_M = 1000

jet_a1_fuel = Fuel(
    energy_density_lhv_MJpL=34.7,  # LHV or HHV?
    density_kgpL=0.804,  # At 15C.
)


lh2_fuel = Fuel(
    energy_density_lhv_MJpL=8.491,
    density_kgpL=70.85e-3,
)

# https://en.wikipedia.org/wiki/Lithium-ion_battery
LION_ENERGY_DENSITY_MJPL = np.mean([0.90, 2.49])
LION_SPECIFIC_ENERGY_MJPKG = np.mean([0.360, 0.954])
lion_fuel = Fuel(
    energy_density_lhv_MJpL=LION_ENERGY_DENSITY_MJPL,
    density_kgpL=(LION_ENERGY_DENSITY_MJPL / LION_SPECIFIC_ENERGY_MJPKG),
)

# https://en.wikipedia.org/wiki/Lithium_polymer_battery
LIPO_ENERGY_DENSITY_MJPL = np.mean([0.90, 2.63])
LIPO_SPECIFIC_ENERGY_MJPKG = np.mean([0.36, 0.95])
lipo_fuel = Fuel(
    energy_density_lhv_MJpL=LIPO_ENERGY_DENSITY_MJPL,
    density_kgpL=(LIPO_ENERGY_DENSITY_MJPL / LIPO_SPECIFIC_ENERGY_MJPKG),
)

turbofan = Propulsion(
    efficiency=0.69,
)


A320_JET_A1_FUEL_CAPACITY_L = 27200
A320_JET_A1_FUEL_CONSUMPTION_RATE_KGPH = 2430


class BaseA320(BaseAirliner):
    cruise_speed_kmph = 829
    fuel_capacity_L = A320_JET_A1_FUEL_CAPACITY_L
    fuel_capacity_kg = A320_JET_A1_FUEL_CAPACITY_L * jet_a1_fuel.density_kgpL
    energy_consumption_rate_MJph = (
        A320_JET_A1_FUEL_CONSUMPTION_RATE_KGPH
        * jet_a1_fuel.specific_energy_lhv_MJpkg
        * turbofan.efficiency
    )


class JetFueledA320(BaseA320):
    propulsion = turbofan
    fuel = jet_a1_fuel


class Lh2FueledA320(BaseA320):
    propulsion = Propulsion(efficiency=turbofan.efficiency)
    fuel = lh2_fuel


class LionFueledA320(BaseA320):
    propulsion = Propulsion(efficiency=turbofan.efficiency)
    fuel = lion_fuel


class LipoFueledA320(BaseA320):
    propulsion = Propulsion(efficiency=turbofan.efficiency)
    fuel = lipo_fuel


at200 = Uav(
    payload_capacity_kg=1500,
    payload_volume_L=(5 * L_PER_CUBIC_M),
)


KM_PER_MILE = 1.609344
DISTANCE_KM_LOOKUP = {
    ("JFK", "LAX"): 2468 * KM_PER_MILE,
    ("JFK", "PIT"): 338 * KM_PER_MILE,
    ("PIT", "DEN"): 1286 * KM_PER_MILE,
    ("DEN", "LAX"): 860 * KM_PER_MILE,
}
duration_str_lookup = {k: (dt.datetime(2000, 1, 1, 0, 0) + dt.timedelta(hours=(v / BaseA320.cruise_speed_kmph))).strftime("%H:%M") for k, v in DISTANCE_KM_LOOKUP.items()}
(dt.datetime(2000, 1, 1, 0, 0) + dt.timedelta(hours=(sum(DISTANCE_KM_LOOKUP[k] for k in [("JFK", "PIT"), ("PIT", "DEN"), ("DEN", "LAX")]) / BaseA320.cruise_speed_kmph))).strftime("%H:%M")
