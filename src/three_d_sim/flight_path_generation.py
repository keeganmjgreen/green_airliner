import dataclasses
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.modeling_objects import (
    KM_PER_LAT_LON,
    Airliner,
    Airplane,
    AirplaneId,
    Location,
    Uav,
    UavId,
    Waypoint,
)
from src.utils.utils import M_PER_KM, SECONDS_PER_HOUR

from .planar_curve_points_generation import generate_planar_curve_points

AirportCode = str
ServiceSide = Literal["to-airport", "from-airport"]

AIRPORT_LOCATIONS_CSV_PATH = "src/three_d_sim/airport_locations.csv"


@dataclasses.dataclass(kw_only=True)
class AirportLocation(Location):
    CODE: AirportCode


def get_all_airport_locations(
    normalize_coords: bool = False,
) -> Dict[AirportCode, AirportLocation]:
    DEFAULT_ALTITUDE = 0.0

    airport_location_df = pd.read_csv(AIRPORT_LOCATIONS_CSV_PATH)
    all_airport_locations = {
        row["airport_code"]: AirportLocation(
            Y_KM=(row["lat"] * KM_PER_LAT_LON),
            X_KM=(row["lon"] * KM_PER_LAT_LON),
            ALTITUDE_KM=row.get("altitude", DEFAULT_ALTITUDE),
            CODE=row["airport_code"],
        )
        for row in airport_location_df.to_dict("records")
    }
    if normalize_coords:
        min_y_km, max_y_km = [
            m(loc.Y_KM for loc in all_airport_locations.values()) for m in [min, max]
        ]
        min_x_km, max_x_km = [
            m(loc.X_KM for loc in all_airport_locations.values()) for m in [min, max]
        ]
        for loc in all_airport_locations.values():
            loc.Y_KM = loc.Y_KM - (min_y_km + max_y_km) / 2
            loc.X_KM = loc.X_KM - (min_x_km + max_x_km) / 2
    return all_airport_locations


ALL_AIRPORT_LOCATIONS = get_all_airport_locations(normalize_coords=True)


@dataclasses.dataclass
class FlightPath:
    takeoff_speed_kmph: float
    takeoff_distance_km: float
    takeoff_leveling_distance_km: float
    rate_of_climb_mps: float
    climb_leveling_distance_km: float
    cruise_altitude_km: float
    cruise_speed_kmph: float
    turning_radius_km: float
    descent_leveling_distance_km: float
    rate_of_descent_mps: float
    landing_leveling_distance_km: float
    landing_distance_km: float
    landing_speed_kmph: float

    def __post_init__(self):
        assert self.takeoff_leveling_distance_km < self.takeoff_distance_km
        assert self.landing_leveling_distance_km < self.landing_distance_km

    @property
    def rate_of_climb_kmph(self) -> float:
        return self.rate_of_climb_mps / M_PER_KM * SECONDS_PER_HOUR

    @property
    def rate_of_descent_kmph(self) -> float:
        return self.rate_of_descent_mps / M_PER_KM * SECONDS_PER_HOUR


@dataclasses.dataclass(kw_only=True)
class AirlinerFlightPath(FlightPath):
    origin_airport: Union[AirportLocation, AirportCode]
    flyover_airports: List[Union[AirportLocation, AirportCode]]
    destination_airport: Union[AirportLocation, AirportCode]
    speed_change_distance_km: float

    def __post_init__(self):
        self.origin_airport = ALL_AIRPORT_LOCATIONS[self.origin_airport]
        self.flyover_airports = [
            ALL_AIRPORT_LOCATIONS[a] for a in self.flyover_airports
        ]
        self.destination_airport = ALL_AIRPORT_LOCATIONS[self.destination_airport]

    @property
    def flyover_airport_codes(self) -> List[AirportCode]:
        return [a.CODE for a in self.flyover_airports]

    @property
    def airports(self) -> List[AirportLocation]:
        return (
            [self.origin_airport] + self.flyover_airports + [self.destination_airport]
        )


@dataclasses.dataclass(kw_only=True)
class UavFlightPath(FlightPath):
    home_airport: Union[AirportLocation, AirportCode]
    arc_radius_km: float
    refueling_altitude_km: float
    refueling_distance_km: float
    service_side: Union[Literal["to_airport", "from_airport"], None] = None
    undocking_distance_from_airport_km: Union[float, None] = None
    airliner_clearance_speed_kmph: Union[float, None] = None
    airliner_clearance_distance_km: Union[float, None] = None
    airliner_clearance_altitude_km: Union[float, None] = None

    def __post_init__(self):
        self.home_airport = ALL_AIRPORT_LOCATIONS[self.home_airport]

    @property
    def AVG_AIRLINER_CLEARANCE_SPEED_KMPH(self) -> Union[float, None]:
        if self.airliner_clearance_speed_kmph is not None:
            return (self.cruise_speed_kmph + self.airliner_clearance_speed_kmph) / 2
        else:
            return None


def _unit_vector(vector: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vector)
    assert norm > 0
    return vector / norm


def _intermediate_point_between(
    point1: np.ndarray, point2: np.ndarray, intermediate_distance: float
) -> np.ndarray:
    vector = point2 - point1
    return point1 + _unit_vector(vector) * intermediate_distance


def orthogonal_xy_vector(vector: np.ndarray) -> np.ndarray:
    vector2 = deepcopy(vector)
    vector2[1], vector2[0] = -vector2[0], vector2[1]
    return vector2


def _angle_between_0_2pi(angle: float) -> float:
    if angle < 0:
        return angle + 2 * np.pi
    else:
        return angle


def _xy_vector_angle(vector: np.ndarray) -> float:
    angle = np.arctan2(vector[1], vector[0])
    angle = _angle_between_0_2pi(angle)
    return angle


def _gen_speed_change_waypoints(
    start_location: Location,
    start_speed_kmph: float,
    end_location: Location,
    end_speed_kmph: float,
    num: int = 50,
    **waypoint_kwargs,
) -> List[Waypoint]:
    distance_km = Location.direct_distance_km_between(start_location, end_location)
    intermediate_distances_km = np.linspace(0, distance_km, num + 1)[1:]
    intermediate_points = [
        _intermediate_point_between(
            start_location.xyz_coords, end_location.xyz_coords, d
        )
        for d in intermediate_distances_km
    ]
    acceleration_kmphph = (end_speed_kmph**2 - start_speed_kmph**2) / (2 * distance_km)
    intermediate_speeds_kmph = np.sqrt(
        start_speed_kmph**2
        + 2
        * acceleration_kmphph
        * (intermediate_distances_km - (distance_km / num) / 2)
    )
    intermediate_waypoints = [
        Waypoint(Location(*point), speed_kmph, **waypoint_kwargs)
        for point, speed_kmph in zip(intermediate_points, intermediate_speeds_kmph)
    ]
    return intermediate_waypoints


def _gen_tmp_speed_change_waypoints(
    start_location: Location,
    default_speed_kmph: float,
    tmp_speed_kmph: float,
    end_location: Location,
    num: int = 50,
    **waypoint_kwargs,
) -> List[Waypoint]:
    distance_km = Location.direct_distance_km_between(start_location, end_location)
    halfway_location = Location(
        *_intermediate_point_between(
            start_location.xyz_coords, end_location.xyz_coords, distance_km / 2
        )
    )
    waypoints = []
    waypoints += _gen_speed_change_waypoints(
        start_location=start_location,
        start_speed_kmph=default_speed_kmph,
        end_location=halfway_location,
        end_speed_kmph=tmp_speed_kmph,
        num=num,
        **waypoint_kwargs,
    )
    waypoints += _gen_speed_change_waypoints(
        start_location=halfway_location,
        start_speed_kmph=tmp_speed_kmph,
        end_location=end_location,
        end_speed_kmph=default_speed_kmph,
        num=num,
        **waypoint_kwargs,
    )
    return waypoints


def _gen_vertical_curve_waypoints(
    sense: Literal["curve-up", "curve-down"],
    direction: Literal["to-tangent", "from-tangent"],
    leveled_altitude_km: float,
    leveled_point: np.ndarray,
    corner_point: np.ndarray,
    tangent_angle: float,
    flight_path: FlightPath,
    flight_path_part: Literal["takeoff", "climb", "descent", "landing"],
    speed_kmph: float,
) -> List[Waypoint]:
    leveling_distance_km = {
        "takeoff": flight_path.takeoff_leveling_distance_km,
        "climb": flight_path.climb_leveling_distance_km,
        "descent": flight_path.descent_leveling_distance_km,
        "landing": flight_path.landing_leveling_distance_km,
    }[flight_path_part]
    first_curve_point = _intermediate_point_between(
        corner_point, leveled_point, leveling_distance_km
    )
    r = leveling_distance_km / np.tan(tangent_angle / 2)  # smoothing radius
    tangent_angles = np.linspace(0, tangent_angle, num=50)
    sign = {
        "curve-up": +1,
        "curve-down": -1,
    }[sense]
    curve_3d_points = np.c_[
        # x, y components:
        (
            first_curve_point
            + r
            * _unit_vector(corner_point - first_curve_point)
            * np.c_[np.sin(tangent_angles)]
        ),
        # z component:
        leveled_altitude_km + sign * r * np.c_[1 - np.cos(tangent_angles)],
    ]
    if direction == "from-tangent":
        curve_3d_points = reversed(curve_3d_points)
    zero_angle_of_attack = (sense == "curve-up" and direction == "from-tangent") or (
        sense == "curve-down" and direction == "to-tangent"
    )
    curve_waypoints = [
        Waypoint(
            Location(*point), speed_kmph, ZERO_ANGLE_OF_ATTACK=zero_angle_of_attack
        )
        for point in curve_3d_points
    ]
    return curve_waypoints


def _gen_altitude_transition_waypoints(
    start_altitude_km: float,
    start_point: np.ndarray,
    end_altitude_km: float,
    eventual_point: np.ndarray,
    flight_path: FlightPath,
    wrt_runway: bool = True,
    inverted: bool = False,
) -> List[Waypoint]:
    kind = +1 if end_altitude_km > start_altitude_km else -1
    invert = +1 if not inverted else -1
    delta_altitude_km = abs(abs(end_altitude_km - start_altitude_km))
    vertical_speed_kmph = {
        +1: flight_path.rate_of_climb_kmph,
        -1: flight_path.rate_of_descent_kmph,
    }[kind * invert]
    duration_h = delta_altitude_km / vertical_speed_kmph
    ground_speed_kmph = np.sqrt(
        flight_path.cruise_speed_kmph**2 - vertical_speed_kmph**2
    )
    ground_distance_km = ground_speed_kmph * duration_h
    angle = np.arctan2(delta_altitude_km, ground_distance_km)

    start_speed_label = {
        +1: "takeoff" if wrt_runway and not inverted else "cruise",
        -1: "landing" if wrt_runway and inverted else "cruise",
    }[kind * invert]
    end_speed_label = {
        +1: "takeoff" if wrt_runway and inverted else "cruise",
        -1: "landing" if wrt_runway and not inverted else "cruise",
    }[kind * invert]
    speed_lookup = {
        "takeoff": flight_path.takeoff_speed_kmph,
        "cruise": flight_path.cruise_speed_kmph,
        "landing": flight_path.landing_speed_kmph,
    }
    start_speed_kmph = speed_lookup[start_speed_label]
    end_speed_kmph = speed_lookup[end_speed_label]

    waypoints = []

    flight_path_part = {
        +1: "takeoff" if wrt_runway and not inverted else "climb",
        -1: "landing" if wrt_runway and inverted else "descent",
    }[kind * invert]
    leveling_distance_km = {
        "takeoff": flight_path.takeoff_leveling_distance_km,
        "climb": flight_path.climb_leveling_distance_km,
        "descent": flight_path.descent_leveling_distance_km,
        "landing": flight_path.landing_leveling_distance_km,
    }[flight_path_part]
    waypoints += _gen_vertical_curve_waypoints(
        sense={+1: "curve-up", -1: "curve-down"}[kind],
        direction="to-tangent",
        leveled_altitude_km=start_altitude_km,
        leveled_point=(2 * start_point - eventual_point),
        corner_point=_intermediate_point_between(
            start_point, eventual_point, leveling_distance_km
        ),
        tangent_angle=angle,
        flight_path=flight_path,
        flight_path_part=flight_path_part,
        speed_kmph=start_speed_kmph,
    )

    climb_leveling_waypoints = _gen_vertical_curve_waypoints(
        sense={+1: "curve-down", -1: "curve-up"}[kind],
        direction="from-tangent",
        leveled_altitude_km=end_altitude_km,
        leveled_point=eventual_point,
        corner_point=_intermediate_point_between(
            start_point, eventual_point, leveling_distance_km + ground_distance_km
        ),
        tangent_angle=angle,
        flight_path=flight_path,
        flight_path_part={
            +1: "takeoff" if wrt_runway and inverted else "climb",
            -1: "landing" if wrt_runway and not inverted else "descent",
        }[kind * invert],
        speed_kmph=end_speed_kmph,
    )

    if wrt_runway:
        waypoints += _gen_speed_change_waypoints(
            start_location=waypoints[-1].LOCATION,
            start_speed_kmph=start_speed_kmph,
            end_location=climb_leveling_waypoints[0].LOCATION,
            end_speed_kmph=end_speed_kmph,
        )

    waypoints += climb_leveling_waypoints

    if inverted:
        waypoints = list(reversed(waypoints))
    return waypoints


def _gen_takeoff_or_landing_waypoints(
    airplane_id: AirplaneId,
    takeoff_or_landing: Literal["takeoff", "landing"],
    airport_location: AirportLocation,
    eventual_point: np.array,
    flight_path: FlightPath,
    altitude_km: Optional[float] = None,
    inverted: bool = False,
) -> List[Waypoint]:
    if altitude_km is None:
        altitude_km = flight_path.cruise_altitude_km

    altitude_transition_waypoints = _gen_altitude_transition_waypoints(
        start_altitude_km=0,
        start_point=_intermediate_point_between(
            airport_location.xy_coords,
            eventual_point,
            intermediate_distance={
                "takeoff": flight_path.takeoff_distance_km,
                "landing": flight_path.landing_distance_km,
            }[takeoff_or_landing],
        ),
        end_altitude_km=altitude_km,
        eventual_point=eventual_point,
        flight_path=flight_path,
        wrt_runway=True,
        inverted=(takeoff_or_landing == "landing"),
    )

    speed_change_waypoints = _gen_speed_change_waypoints(
        start_location=airport_location,
        start_speed_kmph=0,
        end_location=altitude_transition_waypoints[
            0 if takeoff_or_landing == "takeoff" else -1
        ].LOCATION,
        end_speed_kmph={
            "takeoff": flight_path.takeoff_speed_kmph,
            "landing": flight_path.landing_speed_kmph,
        }[takeoff_or_landing],
    )

    if takeoff_or_landing == "takeoff":
        altitude_transition_waypoints[0].LOCATION.TAG = f"{airplane_id}_takeoff_point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{airplane_id}_ascended_point"
        waypoints = speed_change_waypoints + altitude_transition_waypoints
    else:
        altitude_transition_waypoints[0].LOCATION.TAG = f"{airplane_id}_descent_point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{airplane_id}_landing_point"
        speed_change_waypoints[-1].LOCATION.TAG = f"{airplane_id}_landed_point"
        waypoints = altitude_transition_waypoints + list(
            reversed(speed_change_waypoints)
        )

    if inverted:
        waypoints = list(reversed(waypoints))
    return waypoints


def _gen_horizontal_curve_waypoints(
    airplane_id: AirplaneId,
    prev_airport: AirportLocation,
    curr_airport: AirportLocation,
    next_airport: AirportLocation,
    altitude_km: float,
    turning_radius_km: float,
    **waypoint_kwargs: Dict[str, Any],
) -> List[Waypoint]:
    curve_points = generate_planar_curve_points(
        p1=prev_airport.xy_coords,
        p2=curr_airport.xy_coords,
        p3=next_airport.xy_coords,
        R=turning_radius_km,
    )
    curve_waypoints = [
        Waypoint(Location(*point, altitude_km), **waypoint_kwargs)
        for point in curve_points
    ]
    curve_waypoints[0].LOCATION.TAG = (
        f"{airplane_id}_curve_over_{curr_airport.CODE}_start_point"
    )
    curve_waypoints[-1].LOCATION.TAG = (
        f"{airplane_id}_curve_over_{curr_airport.CODE}_end_point"
    )
    return curve_waypoints


def _generate_uav_waypoints(
    airport_A: AirportLocation,
    airport_B: AirportLocation,
    uav_id: AirplaneId,
    uav_fp: UavFlightPath,
    uav_fp_half: Literal["first-half", "second-half"],
    plot: bool = False,
) -> List[Waypoint]:
    A = airport_A.xy_coords
    B = airport_B.xy_coords
    AB = B - A

    if uav_fp.undocking_distance_from_airport_km is not None:
        docking_distance_from_airport_km = (
            uav_fp.refueling_distance_km + uav_fp.undocking_distance_from_airport_km
        )
    else:
        docking_distance_from_airport_km = uav_fp.refueling_distance_km / 2

    # meet and fly together at point H:
    H = _intermediate_point_between(B, A, docking_distance_from_airport_km)

    altitude_transition_waypoints = _gen_altitude_transition_waypoints(
        start_altitude_km=uav_fp.refueling_altitude_km,
        start_point=H,
        end_altitude_km=uav_fp.cruise_altitude_km,
        eventual_point=A,
        flight_path=uav_fp,
        wrt_runway=False,
        inverted=True,
    )

    d = Location.direct_distance_km_between(
        Location(*altitude_transition_waypoints[0].LOCATION.xy_coords), airport_B
    )
    r = uav_fp.arc_radius_km

    F = _intermediate_point_between(B, A, d)

    # centerpoint of uav's arc (circular flight path) = O:
    O = F + orthogonal_xy_vector(_unit_vector(AB)) * r

    # start point of uav's arc (point on its circular flight path) = E:
    E = B - d * np.array(
        [
            AB[0] * (d**2 - r**2) - AB[1] * (2 * r * d),
            AB[1] * (d**2 - r**2) + AB[0] * (2 * r * d),
        ]
    ) / (np.linalg.norm(AB) * (d**2 + r**2))

    phi_E = _xy_vector_angle(E - O)  # angle of segment OE wrt direction <1, 0>
    phi_F = _xy_vector_angle(F - O)  # angle of segment OF wrt direction <1, 0>
    if abs(phi_F - phi_E) <= np.pi:
        if r > 0:
            phi_F -= 2 * np.pi
        else:
            phi_E -= 2 * np.pi
    phis = np.linspace(phi_E, phi_F, num=500)
    uav_arc_points = O + abs(r) * np.c_[np.cos(phis), np.sin(phis)]

    if plot:
        plt.plot(*np.c_[A, B], ".-")
        plt.plot(*np.c_[B, C, D, uav_arc_points.T, H, B], ".-")
        plt.plot(*np.c_[O], ".-")
        ax = plt.gca()
        ax.axis("equal")
        plt.show(block=False)

    uav_arc_waypoints = [
        Waypoint(
            Location(*xy, ALTITUDE_KM=uav_fp.cruise_altitude_km),
            uav_fp.cruise_speed_kmph,
        )
        for i, xy in enumerate(uav_arc_points)
    ]

    takeoff_or_landing_waypoints = _gen_takeoff_or_landing_waypoints(
        airplane_id=uav_id,
        takeoff_or_landing=("takeoff" if uav_fp_half == "first-half" else "landing"),
        airport_location=Location(*B),
        eventual_point=E,
        flight_path=uav_fp,
        inverted=(uav_fp_half == "second-half"),
    )

    if uav_fp_half == "first-half":
        uav_arc_waypoints[0].LOCATION.TAG = f"{uav_id}_arc_start_point"
        uav_arc_waypoints[-1].LOCATION.TAG = f"{uav_id}_arc_end_point"
        altitude_transition_waypoints[0].LOCATION.TAG = (
            f"{uav_id}_descent_to_airliner_point"
        )
        altitude_transition_waypoints[-1].LOCATION.TAG = (
            f"{uav_id}_on_airliner_docking_point"
        )
    elif uav_fp_half == "second-half":
        altitude_transition_waypoints[-1].LOCATION.TAG = (
            f"{uav_id}_on_airliner_undocking_point"
        )
        altitude_transition_waypoints[0].LOCATION.TAG = (
            f"{uav_id}_ascended_from_airliner_point"
        )
        uav_arc_waypoints[-1].LOCATION.TAG = f"{uav_id}_arc_start_point"
        uav_arc_waypoints[0].LOCATION.TAG = f"{uav_id}_arc_end_point"

    uav_waypoints = (
        takeoff_or_landing_waypoints + uav_arc_waypoints + altitude_transition_waypoints
    )

    if uav_fp_half == "second-half":
        uav_waypoints = list(reversed(uav_waypoints))
        # uav_waypoints.append(Waypoint(Location(*B), uav_fp.CRUISE_SPEED_KMPH))

    return uav_waypoints


def generate_all_uav_waypoints(
    uav_id: AirplaneId,
    j: int,
    n_uavs: int,
    uav_fp: UavFlightPath,
    airliner_fp: AirlinerFlightPath,
) -> List[Waypoint]:
    uav_airport = uav_fp.home_airport
    prev_airliner_airport = airliner_fp.airports[
        airliner_fp.airports.index(uav_airport) - 1
    ]
    next_airliner_airport_location = airliner_fp.airports[
        airliner_fp.airports.index(uav_airport) + 1
    ]
    airport_A = (
        prev_airliner_airport
        if uav_fp.service_side == "to_airport"
        else next_airliner_airport_location
    )
    waypoints: List[Waypoint] = []
    waypoints.append(
        Waypoint(
            LOCATION=Location(
                *_intermediate_point_between(
                    uav_airport.xy_coords,
                    airport_A.xy_coords,
                    intermediate_distance=(0.015 * (n_uavs - j)),
                )
            )
        )
    )
    if uav_fp.service_side == "to_airport":
        waypoints += _generate_uav_waypoints(
            airport_A=prev_airliner_airport,
            airport_B=waypoints[0].LOCATION,
            uav_id=uav_id,
            uav_fp=uav_fp,
            uav_fp_half="first-half",
        )
        # UAV takes off from airliner:
        altitude_transition_waypoints = _gen_altitude_transition_waypoints(
            start_altitude_km=uav_fp.refueling_altitude_km,
            start_point=_intermediate_point_between(
                waypoints[-1].LOCATION.xy_coords,
                uav_airport.xy_coords,
                uav_fp.refueling_distance_km,
            ),
            end_altitude_km=uav_fp.cruise_altitude_km,
            eventual_point=uav_airport.xy_coords,
            flight_path=uav_fp,
            wrt_runway=False,
        )
        altitude_transition_waypoints[0].LOCATION.TAG = (
            f"{uav_id}_on_airliner_undocking_point"
        )
        altitude_transition_waypoints[-1].LOCATION.TAG = (
            f"{uav_id}_ascended_from_airliner_point"
        )
        waypoints += altitude_transition_waypoints

        # UAV descends below level of airliner's tail and airliner itself:
        airliner_clearing_duration_h = uav_fp.airliner_clearance_distance_km / (
            airliner_fp.cruise_speed_kmph - uav_fp.AVG_AIRLINER_CLEARANCE_SPEED_KMPH
        )
        airliner_clearing_distance_km = (
            uav_fp.AVG_AIRLINER_CLEARANCE_SPEED_KMPH * airliner_clearing_duration_h
        )
        clearance_point = _intermediate_point_between(
            waypoints[-1].LOCATION.xy_coords,
            uav_airport.xy_coords,
            airliner_clearing_distance_km,
        )
        altitude_transition_waypoints = _gen_altitude_transition_waypoints(
            start_altitude_km=uav_fp.cruise_altitude_km,
            start_point=clearance_point,
            end_altitude_km=uav_fp.airliner_clearance_altitude_km,
            eventual_point=uav_airport.xy_coords,
            flight_path=uav_fp,
            wrt_runway=False,
        )
        altitude_transition_waypoints[0].LOCATION.TAG = f"{uav_id}_lowering_point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{uav_id}_lowered_point"
        waypoints += _gen_tmp_speed_change_waypoints(
            start_location=waypoints[-1].LOCATION,
            default_speed_kmph=uav_fp.cruise_speed_kmph,
            tmp_speed_kmph=uav_fp.airliner_clearance_speed_kmph,
            end_location=altitude_transition_waypoints[0].LOCATION,
        )
        waypoints += altitude_transition_waypoints

        # UAV lands at its airport:
        waypoints += _gen_takeoff_or_landing_waypoints(
            airplane_id=uav_id,
            takeoff_or_landing="landing",
            airport_location=Location(
                *_intermediate_point_between(
                    uav_airport.xy_coords,
                    airport_A.xy_coords,
                    intermediate_distance=(0.015 * (j + 1)),
                )
            ),
            eventual_point=waypoints[-1].LOCATION.xy_coords,
            flight_path=uav_fp,
            altitude_km=uav_fp.airliner_clearance_altitude_km,
        )

    elif uav_fp.service_side == "from_airport":
        last_waypoints = _generate_uav_waypoints(
            airport_A=next_airliner_airport_location,
            airport_B=uav_airport,
            uav_id=uav_id,
            uav_fp=uav_fp,
            uav_fp_half="second-half",
        )

        waypoints += _gen_takeoff_or_landing_waypoints(
            airplane_id=uav_id,
            takeoff_or_landing="takeoff",
            airport_location=deepcopy(waypoints[0].LOCATION),
            eventual_point=next_airliner_airport_location.xy_coords,
            flight_path=uav_fp,
            altitude_km=uav_fp.cruise_altitude_km,
        )
        altitude_transition_waypoints = _gen_altitude_transition_waypoints(
            start_altitude_km=uav_fp.refueling_altitude_km,
            start_point=_intermediate_point_between(
                last_waypoints[0].LOCATION.xy_coords,
                uav_airport.xy_coords,
                uav_fp.refueling_distance_km,
            ),
            end_altitude_km=uav_fp.cruise_altitude_km,
            eventual_point=uav_airport.xy_coords,
            flight_path=uav_fp,
            wrt_runway=False,
            inverted=True,
        )
        altitude_transition_waypoints[0].LOCATION.TAG = (
            f"{uav_id}_descent_to_airliner_point"
        )
        altitude_transition_waypoints[-1].LOCATION.TAG = (
            f"{uav_id}_on_airliner_docking_point"
        )
        waypoints += altitude_transition_waypoints

        waypoints += last_waypoints

    else:
        waypoints += _generate_uav_waypoints(
            airport_A=prev_airliner_airport,
            airport_B=uav_airport,
            uav_id=uav_id,
            uav_fp=uav_fp,
            uav_fp_half="first-half",
        )
        waypoints += _gen_horizontal_curve_waypoints(
            airplane_id=uav_id,
            prev_airport=prev_airliner_airport,
            curr_airport=uav_airport,
            next_airport=next_airliner_airport_location,
            altitude_km=uav_fp.refueling_altitude_km,
            turning_radius_km=uav_fp.turning_radius_km,
            DIRECT_APPROACH_SPEED_KMPH=uav_fp.cruise_speed_kmph,
        )
        waypoints += _generate_uav_waypoints(
            airport_A=next_airliner_airport_location,
            airport_B=uav_airport,
            uav_id=uav_id,
            uav_fp=uav_fp,
            uav_fp_half="second-half",
        )

    waypoints[0].LOCATION.TAG = f"{uav_id}_first_point"

    return waypoints


def get_uav_on_airliner_point(
    airliner_fp: AirlinerFlightPath,
    uav: Uav,
    kind: Literal["docking", "undocking"],
) -> Location:
    point = deepcopy(
        uav.get_tagged_waypoint(
            location_tag=f"{uav.id}_on_airliner_{kind}_point"
        ).LOCATION
    )
    point.ALTITUDE_KM = airliner_fp.cruise_altitude_km
    return point


def _generate_airliner_docking_waypoints(
    airliner_fp: AirlinerFlightPath,
    uavs: Dict[AirportCode, Dict[AirplaneId, Uav]],
    uav_fps: Dict[AirportCode, Dict[AirplaneId, UavFlightPath]],
    i: int,
    service_side: Literal["to_airport", "from_airport"],
    airliner_curve_waypoints: List[Waypoint],
) -> List[Waypoint]:
    waypoints: List[Waypoint] = []

    prev_airport = airliner_fp.airports[i]
    next_airport = airliner_fp.airports[i + 1]

    airport_uavs = list(uavs[next_airport.CODE][service_side].values())
    airport_uav_fps = list(uav_fps[next_airport.CODE][service_side].values())

    for j in range(len(airport_uavs) + 1):
        if j < len(airport_uavs):
            uav = airport_uavs[j]
            uav_fp = airport_uav_fps[j]
            uav_on_airliner_docking_point = get_uav_on_airliner_point(
                airliner_fp, uav, kind="docking"
            )

        if j == 0 and service_side == "to_airport":
            start_location = Location(
                *_intermediate_point_between(
                    (
                        uav_on_airliner_docking_point
                        if len(airport_uavs) > 0
                        else airliner_curve_waypoints[0].LOCATION
                    ).xy_coords,
                    prev_airport.xy_coords,
                    airliner_fp.speed_change_distance_km,
                ),
                ALTITUDE_KM=airliner_fp.cruise_altitude_km,
            )
            start_speed_kmph = airliner_fp.cruise_speed_kmph
        elif len(airport_uavs) > 0:
            prev_uav = airport_uavs[j - 1]
            prev_uav_fp = airport_uav_fps[j - 1]
            prev_uav_on_airliner_undocking_point = get_uav_on_airliner_point(
                airliner_fp, uav=prev_uav, kind="undocking"
            )
            start_location = prev_uav_on_airliner_undocking_point
            start_speed_kmph = prev_uav_fp.cruise_speed_kmph
        else:
            start_location = airliner_curve_waypoints[-1].LOCATION
            start_speed_kmph = 300  # TODO

        if j < len(airport_uavs):
            end_location = uav_on_airliner_docking_point
            end_speed_kmph = uav_fp.cruise_speed_kmph
        elif service_side == "from_airport":
            end_location = Location(
                *_intermediate_point_between(
                    (
                        prev_uav_on_airliner_undocking_point
                        if len(airport_uavs) > 0
                        else airliner_curve_waypoints[-1].LOCATION
                    ).xy_coords,
                    airliner_fp.airports[i + 2].xy_coords,
                    airliner_fp.speed_change_distance_km,
                ),
                ALTITUDE_KM=airliner_fp.cruise_altitude_km,
            )
            end_speed_kmph = airliner_fp.cruise_speed_kmph
        elif len(airport_uavs) == 0:
            end_location = airliner_curve_waypoints[0].LOCATION
            end_speed_kmph = 300  # TODO

        if (
            j == 0
            and service_side == "to_airport"
            or j == len(airport_uavs)
            and service_side == "from_airport"
        ):
            waypoints += _gen_speed_change_waypoints(
                start_location, start_speed_kmph, end_location, end_speed_kmph
            )
        if j < len(airport_uavs):
            waypoints.append(
                Waypoint(
                    uav_on_airliner_docking_point,
                    DIRECT_APPROACH_SPEED_KMPH=uav_fp.cruise_speed_kmph,
                )
            )
            waypoints.append(
                Waypoint(
                    get_uav_on_airliner_point(airliner_fp, uav=uav, kind="undocking"),
                    DIRECT_APPROACH_SPEED_KMPH=uav_fp.cruise_speed_kmph,
                )
            )

    return waypoints


def generate_all_airliner_waypoints(
    airliner_id: AirplaneId,
    airliner_fp: AirlinerFlightPath,
    uavs: Dict[AirportCode, Dict[AirplaneId, Uav]],
    uav_fps: Dict[AirportCode, Dict[AirplaneId, UavFlightPath]],
) -> List[Waypoint]:
    waypoints: List[Waypoint] = []

    for i in range(len(airliner_fp.airports) - 1):
        prev_airport = airliner_fp.airports[i]
        next_airport = airliner_fp.airports[i + 1]

        if i == 0:
            # From first airport...

            waypoints.append(Waypoint(LOCATION=prev_airport))

            waypoints += _gen_takeoff_or_landing_waypoints(
                airplane_id=airliner_id,
                takeoff_or_landing="takeoff",
                airport_location=prev_airport,
                eventual_point=next_airport.xy_coords,
                flight_path=airliner_fp,
            )

        if i < len(airliner_fp.airports) - 2:
            # Between any two airports...

            # Cruise

            curve_waypoints = _gen_horizontal_curve_waypoints(
                airplane_id=airliner_id,
                prev_airport=airliner_fp.airports[i],
                curr_airport=airliner_fp.airports[i + 1],
                next_airport=airliner_fp.airports[i + 2],
                altitude_km=airliner_fp.cruise_altitude_km,
                turning_radius_km=airliner_fp.turning_radius_km,
                DIRECT_APPROACH_SPEED_KMPH=300,  # TODO
            )
            waypoints += _generate_airliner_docking_waypoints(
                airliner_fp,
                uavs,
                uav_fps,
                i,
                service_side="to_airport",
                airliner_curve_waypoints=curve_waypoints,
            )
            waypoints += curve_waypoints
            waypoints += _generate_airliner_docking_waypoints(
                airliner_fp,
                uavs,
                uav_fps,
                i,
                service_side="from_airport",
                airliner_curve_waypoints=curve_waypoints,
            )

        if i == len(airliner_fp.airports) - 2:
            # To last airport...

            waypoints += _gen_takeoff_or_landing_waypoints(
                airplane_id=airliner_id,
                takeoff_or_landing="landing",
                airport_location=next_airport,
                eventual_point=prev_airport.xy_coords,
                flight_path=airliner_fp,
            )

    return waypoints


def delay_uavs(uavs: Dict[AirportCode, Dict[UavId, Uav]], airliner: Airliner) -> None:
    for airport_uavs in uavs.values():
        for uav in airport_uavs.values():
            uav_travel_duration_to_docking_point = (
                uav.get_travel_durations_to_tagged_waypoints()[
                    f"{uav.id}_on_airliner_docking_point"
                ]
            )
            airliner_travel_duration_to_docking_point = (
                airliner.get_travel_durations_to_tagged_waypoints()[
                    f"{uav.id}_on_airliner_docking_point"
                ]
            )
            assert (
                uav_travel_duration_to_docking_point
                <= airliner_travel_duration_to_docking_point
            )
            uav.waypoints[0].TIME_INTO_SIMULATION = (
                airliner_travel_duration_to_docking_point
                - uav_travel_duration_to_docking_point
            )


def write_airplane_paths(airplanes: List[Airplane]) -> None:
    for airplane in airplanes:
        fpath = Path(f"tmp/airplane_paths/{airplane.id}.csv")
        fpath.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(airplane.all_locations).to_csv(
            fpath,
            header=False,
            index=False,
            float_format="%f",
        )


def write_airplane_tagged_waypoints(airplanes: List[Airplane]) -> None:
    for airplane in airplanes:
        fpath = Path(f"tmp/airplane_tagged_waypoints/{airplane.id}.csv")
        fpath.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(airplane.all_tagged_waypoints).drop(columns=["TAG"]).to_csv(
            fpath,
            header=False,
            index=False,
            float_format="%f",
        )


def viz_airplane_paths(airplanes: List[Airplane]) -> None:
    def _speed_to_color(speed_kmph: float) -> np.array:
        MIN_SPEED_RGB = np.array([0, 0, 1])
        MIN_SPEED_KMPH = 0
        MAX_SPEED_RGB = np.array([1, 0, 0])
        MAX_SPEED_KMPH = 1000
        speed_rgb = (speed_kmph - MIN_SPEED_KMPH) / (
            MAX_SPEED_KMPH - MIN_SPEED_KMPH
        ) * (MAX_SPEED_RGB - MIN_SPEED_RGB) + MIN_SPEED_RGB
        return speed_rgb

    fig = go.Figure()
    for airplane in airplanes:
        speeds_kmph = [wp.DIRECT_APPROACH_SPEED_KMPH for wp in airplane.waypoints]
        all_locations = airplane.all_locations
        pair_segments = list(zip(all_locations[1:], all_locations[:-1]))
        for pair_segment, speed_kmph in zip(pair_segments, speeds_kmph):
            x, y, z = np.c_[pair_segment]
            fig.add_scatter3d(
                x=x,
                y=y,
                z=z,
                line=dict(color=([_speed_to_color(speed_kmph)] * 2), width=4),
                mode="lines",
                showlegend=False,
            )
    fig.layout.scene.aspectmode = "data"
    fig.show()
