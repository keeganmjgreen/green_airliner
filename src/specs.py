import datetime as dt
from typing import Any, Dict, Type

import numpy as np

from src.feasibility_study.modeling_objects import BaseAirliner, Fuel, Propulsion, Uav
from src.utils.utils import L_PER_CUBIC_M

jet_a1_fuel = Fuel(
    energy_density_lhv_MJpL=34.7,  # LHV or HHV?
    density_kgpL=0.804,  # At 15C.
)

lh2_fuel = Fuel(
    energy_density_lhv_MJpL=8.491,  # From https://en.wikipedia.org/wiki/Energy_density
    density_kgpL=70.85e-3,  # From https://en.wikipedia.org/wiki/Liquid_hydrogen
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

BP_AVGAS_80_SPECIFIC_ENERGY_MJPKG = 44.65  # https://en.wikipedia.org/wiki/Aviation_fuel > Energy content
AVGAS_DENSITY_KGPL = 0.720  # https://en.wikipedia.org/wiki/Avgas > Properties
avgas = Fuel(
    energy_density_lhv_MJpL=(BP_AVGAS_80_SPECIFIC_ENERGY_MJPKG * AVGAS_DENSITY_KGPL),
    density_kgpL=AVGAS_DENSITY_KGPL,
)

turbofan = Propulsion(
    efficiency=0.69,
)
turboprop = Propulsion(
    efficiency=0.8,
    # ^ Approximated from https://en.wikipedia.org/wiki/Turboprop#/media/File:Propulsive_efficiency_for_different_engine_types_and_Mach_numbers.png
    #     given a mach number of 0.2428 (`At200.cruise_speed_kmph`).
)


class BaseA320(BaseAirliner):
    cruise_speed_kmph = 829
    fuel_capacity_L = 27200
    fuel_capacity_kg = fuel_capacity_L * jet_a1_fuel.density_kgpL
    energy_consumption_rate_MJ_per_km = (
        2430  # kg/h
        * jet_a1_fuel.specific_energy_lhv_MJpkg
        * turbofan.efficiency
        / cruise_speed_kmph
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


class At200(Uav):
    cruise_speed_kmph = 300
    fuel_capacity_L = 1256
    """From https://www.aerospace.co.nz/files/dmfile/PAL%202016%20P-750%20XSTOL%20Brochure%20final.pdf300."""
    _fuel_consumption_rate_l_per_h = 184
    energy_consumption_rate_MJ_per_km = (
        jet_a1_fuel.energy_density_lhv_MJpL  # TODO: Replace with avgas.
        * _fuel_consumption_rate_l_per_h
        / cruise_speed_kmph
    )
    propulsion = turboprop
    fuel = avgas
    payload_capacity_kg = 1500
    payload_volume_L = 5 * L_PER_CUBIC_M


airliners = [
    JetFueledA320,
    Lh2FueledA320,
    LionFueledA320,
    LipoFueledA320,
]
uavs = [
    At200,
]
airliner_lookup: Dict[str, Type[BaseAirliner]] = {x.__name__: x for x in airliners}
uav_lookup: Dict[str, Type[Uav]] = {x.__name__: x for x in uavs}


KM_PER_MILE = 1.609344
DISTANCE_KM_LOOKUP = {
    ("JFK", "LAX"): 2468 * KM_PER_MILE,
    ("JFK", "PIT"): 338 * KM_PER_MILE,
    ("PIT", "DEN"): 1286 * KM_PER_MILE,
    ("DEN", "LAX"): 860 * KM_PER_MILE,
}
