from src.modeling_objects import (
    Airliner,
    AirlinerFlightPath,
    AirportCode,
    Fuel,
    ServiceSide,
    Uav,
    UavFlightPath,
    UavId,
)
from src.utils.utils import MJ_PER_KWH

from .airplane_waypoints_generation import (
    generate_all_airliner_waypoints,
    generate_all_uav_waypoints,
)
from .simulation_config_schema import SimulationConfig


def make_airplanes(
    simulation_config: SimulationConfig,
) -> tuple[Airliner, dict[AirportCode, dict[ServiceSide, dict[UavId, Uav]]]]:
    airliner_config = simulation_config.airliner_config
    airliner = Airliner(
        airplane_spec=airliner_config.airplane_spec,
        refueling_rate_kW=airliner_config.refueling_rate_kW,
        initial_energy_level_pc=airliner_config.initial_energy_level_pc,
        viz_model=airliner_config.viz_model_name,
    )
    airliner.flight_path = AirlinerFlightPath.from_configs(
        simulation_config.airliner_flight_path_config, airliner_config
    )

    uavs = _make_uavs(
        simulation_config,
        fuel=airliner.airplane_spec.fuel,
        airliner_fp=airliner.flight_path,
    )

    waypoints = generate_all_airliner_waypoints(airliner.id, airliner.flight_path, uavs)
    airliner.location = waypoints.pop(0).LOCATION
    airliner.waypoints = waypoints

    return airliner, uavs


def _make_uavs(
    simulation_config: SimulationConfig, fuel: Fuel, airliner_fp: AirlinerFlightPath
) -> dict[AirportCode, dict[ServiceSide, dict[UavId, Uav]]]:
    uavs = {}
    for uav_airport_code, x in simulation_config.n_uavs_per_flyover_airport.items():
        airport_uav_idx = 0
        uavs[uav_airport_code] = {}
        for service_side, n_uavs in x.dict().items():
            uavs[uav_airport_code][service_side] = {}
            for service_side_uav_idx in range(n_uavs):
                uav = _make_uav(
                    simulation_config,
                    fuel,
                    airliner_fp,
                    uav_airport_code,
                    airport_uav_idx,
                    service_side,
                    n_uavs,
                    service_side_uav_idx,
                )
                # Add the UAV to the `uavs` dict:
                uavs[uav_airport_code][service_side][uav.id] = uav

                airport_uav_idx += 1

    return uavs


def _make_uav(
    simulation_config: SimulationConfig,
    fuel: Fuel,
    airliner_fp: AirlinerFlightPath,
    uav_airport_code: AirportCode,
    airport_uav_idx: int,
    service_side: ServiceSide,
    n_uavs: int,
    service_side_uav_idx: int,
) -> Uav:
    uavs_config = simulation_config.uavs_config
    # Instantiate the UAV:
    uav = Uav(
        id=f"{uav_airport_code}_UAV_{airport_uav_idx}",
        airplane_spec=uavs_config.airplane_spec,
        refueling_rate_kW=uavs_config.refueling_rate_kW,
        initial_energy_level_pc=uavs_config.initial_energy_level_pc,
        viz_model=uavs_config.viz_model_name,
        payload_fuel=fuel,
        initial_refueling_energy_level_pc=uavs_config.initial_refueling_energy_level_pc,
    )

    refueling_rate_kW = min(
        simulation_config.airliner_config.refueling_rate_kW,
        simulation_config.uavs_config.refueling_rate_kW,
    )
    refueling_distance_km = (
        uavs_config.airplane_spec.cruise_speed_kmph
        * uav.refueling_energy_capacity_MJ
        / refueling_rate_kW
        / MJ_PER_KWH
    )
    decreasing_towards_airport = (
        service_side_uav_idx
        if service_side == "from_airport"
        else (n_uavs - service_side_uav_idx - 1)
    )
    uavs_fp_config = simulation_config.uavs_flight_path_config
    # Instantiate the UAV Flight Path:
    uav.flight_path = UavFlightPath(
        home_airport=uav_airport_code,
        takeoff_speed_kmph=uavs_fp_config.takeoff_speed_kmph,
        takeoff_distance_km=uavs_fp_config.takeoff_distance_km,
        takeoff_leveling_distance_km=uavs_fp_config.takeoff_leveling_distance_km,
        rate_of_climb_mps=uavs_fp_config.rate_of_climb_mps,
        climb_leveling_distance_km=uavs_fp_config.climb_leveling_distance_km,
        cruise_altitude_km=(
            uavs_fp_config.smallest_cruise_altitude_km
            + uavs_fp_config.inter_uav_vertical_distance_km * service_side_uav_idx
        ),
        cruise_speed_kmph=uavs_config.airplane_spec.cruise_speed_kmph,
        turning_radius_km=airliner_fp.turning_radius_km,
        descent_leveling_distance_km=uavs_fp_config.descent_leveling_distance_km,
        rate_of_descent_mps=uavs_fp_config.rate_of_descent_mps,
        landing_leveling_distance_km=uavs_fp_config.landing_leveling_distance_km,
        landing_distance_km=uavs_fp_config.landing_distance_km,
        landing_speed_kmph=uavs_fp_config.landing_speed_kmph,
        arc_radius_km=uavs_fp_config.arc_radius_km,
        refueling_altitude_km=(
            airliner_fp.cruise_altitude_km
            + uavs_fp_config.airliner_uav_docking_distance_km
        ),
        refueling_distance_km=refueling_distance_km,
        service_side=service_side,
        undocking_distance_from_airport_km=(
            uavs_fp_config.smallest_undocking_distance_from_airport_km
            + (refueling_distance_km + uavs_fp_config.inter_uav_clearance_km)
            * decreasing_towards_airport
        ),
        airliner_clearance_speed_kmph=uavs_fp_config.airliner_clearance_speed_kmph,
        airliner_clearance_distance_km=uavs_fp_config.airliner_clearance_distance_km,
        airliner_clearance_altitude_km=(
            uavs_fp_config.smallest_airliner_clearance_altitude_km
            + uavs_fp_config.inter_uav_vertical_distance_km * service_side_uav_idx
        ),
    )

    waypoints = generate_all_uav_waypoints(
        uav.id, service_side_uav_idx, n_uavs, uav.flight_path, airliner_fp
    )
    uav.location = waypoints.pop(0).LOCATION
    uav.waypoints = waypoints

    return uav
