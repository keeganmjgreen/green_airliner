import dataclasses

import numpy as np


@dataclasses.dataclass
class Fuel:
    energy_density_lhv_MJpL: float  # LHV = Lower Heating Value.
    density_kgpL: float

    @property
    def specific_energy_lhv_MJpkg(self) -> float:
        return self.energy_density_lhv_MJpL / self.density_kgpL


@dataclasses.dataclass
class Propulsion:
    efficiency: float


def get_energy_capacity_MJ(
    fuel_capacity_L: float, fuel_capacity_kg: float, fuel: Fuel
) -> float:
    energy_capacity_MJ = min(
        fuel_capacity_L * fuel.energy_density_lhv_MJpL,
        fuel_capacity_kg * fuel.specific_energy_lhv_MJpkg,
    )
    if energy_capacity_MJ == fuel_capacity_L * fuel.energy_density_lhv_MJpL:
        print(
            "Fuel volume capacity (L) or fuel energy density (MJ/L) is limiting factor. ",
            end="",
        )
    if energy_capacity_MJ == fuel_capacity_kg * fuel.specific_energy_lhv_MJpkg:
        print(
            "Fuel weight capacity (kg) or fuel specific energy (MJ/kg) is limiting factor. ",
            end="",
        )
    print()
    return energy_capacity_MJ


@dataclasses.dataclass
class BaseAirplane:
    # Sub-class (e.g., `A320`) attributes:
    cruise_speed_kmph: float = dataclasses.field(init=False)
    fuel_capacity_L: float = dataclasses.field(init=False)
    """Analogous to total volume of energy storage medium (e.g., jet fuel)."""
    energy_consumption_rate_MJ_per_km: float = dataclasses.field(init=False)

    # Sub-sub-class (e.g., `JetFueledA320`) attributes:
    propulsion: Propulsion = dataclasses.field(init=False)
    fuel: Fuel = dataclasses.field(init=False)


@dataclasses.dataclass
class BaseAirliner(BaseAirplane):
    fuel_capacity_kg: float = dataclasses.field(init=False)

    # Sub-sub-class instance (e.g., `JetFueledA320()`) attributes:
    reserve_energy_thres_MJ: float
    # The following attributes are designed to be mutated.
    energy_quantity_MJ: float = dataclasses.field(init=False)
    time_into_flight_h = 0

    @classmethod
    @property
    def energy_capacity_MJ(cls) -> float:
        return get_energy_capacity_MJ(
            cls.fuel_capacity_L, cls.fuel_capacity_kg, cls.fuel
        )

    def fly(self, distance_km: float) -> None:
        time_delta_h = distance_km / self.cruise_speed_kmph
        self.time_into_flight_h += time_delta_h
        self.energy_quantity_MJ -= (
            self.energy_consumption_rate_MJ_per_km
            * self.cruise_speed_kmph
            / self.propulsion.efficiency
        ) * time_delta_h

    def calculate_range_km(self, energy_quantity_MJ: float) -> float:
        range_h = (energy_quantity_MJ - self.reserve_energy_thres_MJ) / (
            self.energy_consumption_rate_MJ_per_km
            * self.cruise_speed_kmph
            / self.propulsion.efficiency
        )
        range_km = range_h * self.cruise_speed_kmph
        return range_km

    def refuel(self, energy_quantity_MJ: float) -> None:
        self.energy_quantity_MJ += energy_quantity_MJ
        self.energy_quantity_MJ = np.clip(
            a=self.energy_quantity_MJ, a_min=None, a_max=self.energy_capacity_MJ
        )


@dataclasses.dataclass
class Uav(BaseAirplane):
    payload_volume_L: float
    payload_capacity_kg: float

    @classmethod
    @property
    def energy_capacity_MJ(cls) -> float:
        return cls.fuel_capacity_L * cls.fuel.energy_density_lhv_MJpL

    @classmethod
    def refueling_energy_capacity_MJ(cls, fuel: Fuel) -> float:
        return get_energy_capacity_MJ(
            fuel_capacity_L=cls.payload_volume_L,
            fuel_capacity_kg=cls.payload_capacity_kg,
            fuel=fuel,
        )
