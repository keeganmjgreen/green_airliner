import dataclasses
import datetime as dt
from copy import deepcopy
from typing import Any, Dict, List, Literal, Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.modeling_objects import (
    AirplaneId,
    KM_PER_LAT_LON,
    Airliner,
    Airplane,
    Location,
    Uav,
)
from src.modeling_objects import Waypoint
from src.utils.utils import M_PER_KM, SECONDS_PER_HOUR

from .planar_curve_points_generation import generate_planar_curve_points

AIRPORT_CODE_TYPE = str

AIRPORT_LOCATIONS_CSV_PATH = "src/three_d_sim/airport_locations.csv"


@dataclasses.dataclass(kw_only=True)
class AirportLocation(Location):
    CODE: AIRPORT_CODE_TYPE


def get_all_airport_locations(
    normalize_coords: bool = False,
) -> Dict[AIRPORT_CODE_TYPE, AirportLocation]:
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
    # START_TIMESTAMP: dt.datetime
    AIRPORT_CODES: List[AIRPORT_CODE_TYPE]
    TAKEOFF_SPEED_KMPH: float
    TAKEOFF_DISTANCE_KM: float
    TAKEOFF_LEVELING_DISTANCE_KM: float
    RATE_OF_CLIMB_MPS: float
    CLIMB_LEVELING_DISTANCE_KM: float
    CRUISE_ALTITUDE_KM: float
    CRUISE_SPEED_KMPH: float
    TURNING_RADIUS_KM: float
    DESCENT_LEVELING_DISTANCE_KM: float
    RATE_OF_DESCENT_MPS: float
    LANDING_LEVELING_DISTANCE_KM: float
    LANDING_DISTANCE_KM: float
    LANDING_SPEED_KMPH: float

    def __post_init__(self):
        assert self.TAKEOFF_LEVELING_DISTANCE_KM < self.TAKEOFF_DISTANCE_KM
        assert self.LANDING_LEVELING_DISTANCE_KM < self.LANDING_DISTANCE_KM

    @property
    def AIRPORT_LOCATIONS(self) -> List[AirportLocation]:
        return [ALL_AIRPORT_LOCATIONS[ac] for ac in self.AIRPORT_CODES]

    @property
    def RATE_OF_CLIMB_KMPH(self) -> float:
        return self.RATE_OF_CLIMB_MPS / M_PER_KM * SECONDS_PER_HOUR

    @property
    def RATE_OF_DESCENT_KMPH(self) -> float:
        return self.RATE_OF_DESCENT_MPS / M_PER_KM * SECONDS_PER_HOUR


@dataclasses.dataclass(kw_only=True)
class AirlinerFlightPath(FlightPath):
    SPEED_CHANGE_DISTANCE_KM: float


@dataclasses.dataclass(kw_only=True)
class UavFlightPath(FlightPath):
    ARC_RADIUS_KM: float
    REFUELING_ALTITUDE_KM: float
    REFUELING_DISTANCE_KM: float
    SERVICE_SIDE: Union[Literal["to-airport", "from-airport"], None] = None
    UNDOCKING_DISTANCE_FROM_AIRPORT_KM: Union[float, None] = None
    AIRLINER_CLEARANCE_SPEED_KMPH: Union[float, None] = None
    AIRLINER_CLEARANCE_DISTANCE_KM: Union[float, None] = None
    AIRLINER_CLEARANCE_ALTITUDE_KM: Union[float, None] = None

    @property
    def AVG_AIRLINER_CLEARANCE_SPEED_KMPH(self) -> Union[float, None]:
        if self.AIRLINER_CLEARANCE_SPEED_KMPH is not None:
            return (self.CRUISE_SPEED_KMPH + self.AIRLINER_CLEARANCE_SPEED_KMPH) / 2
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
    flight_path_part: Literal["TAKEOFF", "CLIMB", "DESCENT", "LANDING"],
    speed_kmph: float,
) -> List[Waypoint]:
    leveling_distance_km = getattr(
        flight_path, flight_path_part + "_LEVELING_DISTANCE_KM"
    )
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
    vertical_speed_kmph = getattr(
        flight_path, "RATE_OF_" + {+1: "CLIMB", -1: "DESCENT"}[kind * invert] + "_KMPH"
    )
    duration_h = delta_altitude_km / vertical_speed_kmph
    ground_speed_kmph = np.sqrt(
        flight_path.CRUISE_SPEED_KMPH**2 - vertical_speed_kmph**2
    )
    ground_distance_km = ground_speed_kmph * duration_h
    angle = np.arctan2(delta_altitude_km, ground_distance_km)

    start_speed_label = {
        +1: "TAKEOFF" if wrt_runway and not inverted else "CRUISE",
        -1: "LANDING" if wrt_runway and inverted else "CRUISE",
    }[kind * invert]
    end_speed_label = {
        +1: "TAKEOFF" if wrt_runway and inverted else "CRUISE",
        -1: "LANDING" if wrt_runway and not inverted else "CRUISE",
    }[kind * invert]
    start_speed_kmph = getattr(flight_path, f"{start_speed_label}_SPEED_KMPH")
    end_speed_kmph = getattr(flight_path, f"{end_speed_label}_SPEED_KMPH")

    waypoints = []

    flight_path_part = {
        +1: "TAKEOFF" if wrt_runway and not inverted else "CLIMB",
        -1: "LANDING" if wrt_runway and inverted else "DESCENT",
    }[kind * invert]
    leveling_distance_km = getattr(
        flight_path, flight_path_part + "_LEVELING_DISTANCE_KM"
    )
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
            +1: "TAKEOFF" if wrt_runway and inverted else "CLIMB",
            -1: "LANDING" if wrt_runway and not inverted else "DESCENT",
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
    takeoff_or_landing: Literal["TAKEOFF", "LANDING"],
    airport_location: AirportLocation,
    eventual_point: np.array,
    flight_path: FlightPath,
    altitude_km: Optional[float] = None,
    inverted: bool = False,
) -> List[Waypoint]:
    if altitude_km is None:
        altitude_km = flight_path.CRUISE_ALTITUDE_KM

    altitude_transition_waypoints = _gen_altitude_transition_waypoints(
        start_altitude_km=0,
        start_point=_intermediate_point_between(
            airport_location.xy_coords,
            eventual_point,
            getattr(flight_path, f"{takeoff_or_landing}_DISTANCE_KM"),
        ),
        end_altitude_km=altitude_km,
        eventual_point=eventual_point,
        flight_path=flight_path,
        wrt_runway=True,
        inverted=(takeoff_or_landing == "LANDING"),
    )

    speed_change_waypoints = _gen_speed_change_waypoints(
        start_location=airport_location,
        start_speed_kmph=0,
        end_location=altitude_transition_waypoints[
            0 if takeoff_or_landing == "TAKEOFF" else -1
        ].LOCATION,
        end_speed_kmph=getattr(flight_path, f"{takeoff_or_landing}_SPEED_KMPH"),
    )

    if takeoff_or_landing == "TAKEOFF":
        altitude_transition_waypoints[0].LOCATION.TAG = f"{airplane_id}-takeoff-point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{airplane_id}-ascended-point"
        waypoints = speed_change_waypoints + altitude_transition_waypoints
    else:
        altitude_transition_waypoints[0].LOCATION.TAG = f"{airplane_id}-descent-point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{airplane_id}-landing-point"
        speed_change_waypoints[-1].LOCATION.TAG = f"{airplane_id}-landed-point"
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
    curve_waypoints[0].LOCATION.TAG = f"{airplane_id}-curve-over-{curr_airport.CODE}-start-point"
    curve_waypoints[-1].LOCATION.TAG = f"{airplane_id}-curve-over-{curr_airport.CODE}-end-point"
    return curve_waypoints


def _generate_uav_waypoints(
    airport_A: AirportLocation,
    airport_B: AirportLocation,
    uav: Uav,
    uav_fp: UavFlightPath,
    uav_fp_half: Literal["first-half", "second-half"],
    plot: bool = False,
) -> List[Waypoint]:
    A = airport_A.xy_coords
    B = airport_B.xy_coords
    AB = B - A

    if uav_fp.UNDOCKING_DISTANCE_FROM_AIRPORT_KM is not None:
        docking_distance_from_airport_km = (
            uav_fp.REFUELING_DISTANCE_KM + uav_fp.UNDOCKING_DISTANCE_FROM_AIRPORT_KM
        )
    else:
        docking_distance_from_airport_km = uav_fp.REFUELING_DISTANCE_KM / 2

    # meet and fly together at point H:
    H = _intermediate_point_between(B, A, docking_distance_from_airport_km)

    altitude_transition_waypoints = _gen_altitude_transition_waypoints(
        start_altitude_km=uav_fp.REFUELING_ALTITUDE_KM,
        start_point=H,
        end_altitude_km=uav_fp.CRUISE_ALTITUDE_KM,
        eventual_point=A,
        flight_path=uav_fp,
        wrt_runway=False,
        inverted=True,
    )

    d = Location.direct_distance_km_between(
        Location(*altitude_transition_waypoints[0].LOCATION.xy_coords), airport_B
    )
    r = uav_fp.ARC_RADIUS_KM

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
            Location(*xy, ALTITUDE_KM=uav_fp.CRUISE_ALTITUDE_KM),
            uav_fp.CRUISE_SPEED_KMPH,
        )
        for i, xy in enumerate(uav_arc_points)
    ]

    takeoff_or_landing_waypoints = _gen_takeoff_or_landing_waypoints(
        airplane_id=uav.ID,
        takeoff_or_landing=(
            "TAKEOFF" if uav_fp_half == "first-half" else "LANDING"
        ),
        airport_location=Location(*B),
        eventual_point=E,
        flight_path=uav_fp,
        inverted=(uav_fp_half == "second-half"),
    )

    if uav_fp_half == "first-half":
        uav_arc_waypoints[0].LOCATION.TAG = f"{uav.ID}-arc-start-point"
        uav_arc_waypoints[-1].LOCATION.TAG = f"{uav.ID}-arc-end-point"
        altitude_transition_waypoints[0].LOCATION.TAG = f"{uav.ID}-descent-to-airliner-point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{uav.ID}-on-airliner-docking-point"
    elif uav_fp_half == "second-half":
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{uav.ID}-on-airliner-undocking-point"
        altitude_transition_waypoints[0].LOCATION.TAG = f"{uav.ID}-ascended-from-airliner-point"
        uav_arc_waypoints[-1].LOCATION.TAG = f"{uav.ID}-arc-start-point"
        uav_arc_waypoints[0].LOCATION.TAG = f"{uav.ID}-arc-end-point"

    uav_waypoints = takeoff_or_landing_waypoints + uav_arc_waypoints + altitude_transition_waypoints

    if uav_fp_half == "second-half":
        uav_waypoints = list(reversed(uav_waypoints))
        # uav_waypoints.append(Waypoint(Location(*B), uav_fp.CRUISE_SPEED_KMPH))

    return uav_waypoints


def provision_uav_from_flight_path(
    uav: Uav, j: int, n_uavs: int, uav_fp: UavFlightPath, airliner_fp: FlightPath
) -> None:
    assert len(uav_fp.AIRPORT_LOCATIONS) == 1
    uav_airport_location = uav_fp.AIRPORT_LOCATIONS[0]
    prev_airliner_airport_location = airliner_fp.AIRPORT_LOCATIONS[
        airliner_fp.AIRPORT_LOCATIONS.index(uav_airport_location) - 1
    ]
    next_airliner_airport_location = airliner_fp.AIRPORT_LOCATIONS[
        airliner_fp.AIRPORT_LOCATIONS.index(uav_airport_location) + 1
    ]
    airport_A = prev_airliner_airport_location if uav_fp.SERVICE_SIDE == "to-airport" else next_airliner_airport_location
    uav.location = Location(
        *_intermediate_point_between(uav_airport_location.xy_coords, airport_A.xy_coords, intermediate_distance=(0.015 * (n_uavs - j)))
    )
    # uav.set_heading(...)  # TODO?
    if uav_fp.SERVICE_SIDE == "to-airport":
        uav.waypoints += _generate_uav_waypoints(
            airport_A=prev_airliner_airport_location,
            airport_B=uav.location,
            uav=uav,
            uav_fp=uav_fp,
            uav_fp_half="first-half",
        )
        # UAV takes off from airliner:
        altitude_transition_waypoints = _gen_altitude_transition_waypoints(
            start_altitude_km=uav_fp.REFUELING_ALTITUDE_KM,
            start_point=_intermediate_point_between(
                uav.waypoints[-1].LOCATION.xy_coords,
                uav_airport_location.xy_coords,
                uav_fp.REFUELING_DISTANCE_KM,
            ),
            end_altitude_km=uav_fp.CRUISE_ALTITUDE_KM,
            eventual_point=uav_airport_location.xy_coords,
            flight_path=uav_fp,
            wrt_runway=False,
        )
        altitude_transition_waypoints[0].LOCATION.TAG = (
            f"{uav.ID}-on-airliner-undocking-point"
        )
        altitude_transition_waypoints[-1].LOCATION.TAG = (
            f"{uav.ID}-ascended-from-airliner-point"
        )
        uav.waypoints += altitude_transition_waypoints

        # UAV descends below level of airliner's tail and airliner itself:
        airliner_clearing_duration_h = uav_fp.AIRLINER_CLEARANCE_DISTANCE_KM / (
            airliner_fp.CRUISE_SPEED_KMPH - uav_fp.AVG_AIRLINER_CLEARANCE_SPEED_KMPH
        )
        airliner_clearing_distance_km = (
            uav_fp.AVG_AIRLINER_CLEARANCE_SPEED_KMPH * airliner_clearing_duration_h
        )
        clearance_point = _intermediate_point_between(
            uav.waypoints[-1].LOCATION.xy_coords,
            uav_airport_location.xy_coords,
            airliner_clearing_distance_km,
        )
        altitude_transition_waypoints = _gen_altitude_transition_waypoints(
            start_altitude_km=uav_fp.CRUISE_ALTITUDE_KM,
            start_point=clearance_point,
            end_altitude_km=uav_fp.AIRLINER_CLEARANCE_ALTITUDE_KM,
            eventual_point=uav_airport_location.xy_coords,
            flight_path=uav_fp,
            wrt_runway=False,
        )
        altitude_transition_waypoints[0].LOCATION.TAG = f"{uav.ID}-lowering-point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{uav.ID}-lowered-point"
        uav.waypoints += _gen_tmp_speed_change_waypoints(
            start_location=uav.waypoints[-1].LOCATION,
            default_speed_kmph=uav_fp.CRUISE_SPEED_KMPH,
            tmp_speed_kmph=uav_fp.AIRLINER_CLEARANCE_SPEED_KMPH,
            end_location=altitude_transition_waypoints[0].LOCATION,
        )
        uav.waypoints += altitude_transition_waypoints

        # UAV lands at its airport:
        uav.waypoints += _gen_takeoff_or_landing_waypoints(
            airplane_id=uav.ID,
            takeoff_or_landing="LANDING",
            airport_location=Location(
                *_intermediate_point_between(uav_airport_location.xy_coords, airport_A.xy_coords, intermediate_distance=(0.015 * (j + 1)))
            ),
            eventual_point=uav.waypoints[-1].LOCATION.xy_coords,
            flight_path=uav_fp,
            altitude_km=uav_fp.AIRLINER_CLEARANCE_ALTITUDE_KM,
        )

    elif uav_fp.SERVICE_SIDE == "from-airport":
        last_waypoints = _generate_uav_waypoints(
            airport_A=next_airliner_airport_location,
            airport_B=uav_airport_location,
            uav=uav,
            uav_fp=uav_fp,
            uav_fp_half="second-half",
        )

        uav.waypoints += _gen_takeoff_or_landing_waypoints(
            airplane_id=uav.ID,
            takeoff_or_landing="TAKEOFF",
            airport_location=deepcopy(uav.location),
            eventual_point=next_airliner_airport_location.xy_coords,
            flight_path=uav_fp,
            altitude_km=uav_fp.CRUISE_ALTITUDE_KM,
        )
        altitude_transition_waypoints = _gen_altitude_transition_waypoints(
            start_altitude_km=uav_fp.REFUELING_ALTITUDE_KM,
            start_point=_intermediate_point_between(
                last_waypoints[0].LOCATION.xy_coords,
                uav_airport_location.xy_coords,
                uav_fp.REFUELING_DISTANCE_KM,
            ),
            end_altitude_km=uav_fp.CRUISE_ALTITUDE_KM,
            eventual_point=uav_airport_location.xy_coords,
            flight_path=uav_fp,
            wrt_runway=False,
            inverted=True,
        )
        altitude_transition_waypoints[0].LOCATION.TAG = f"{uav.ID}-descent-to-airliner-point"
        altitude_transition_waypoints[-1].LOCATION.TAG = f"{uav.ID}-on-airliner-docking-point"
        uav.waypoints += altitude_transition_waypoints

        uav.waypoints += last_waypoints

    else:
        uav.waypoints += _generate_uav_waypoints(
            airport_A=prev_airliner_airport_location,
            airport_B=uav_airport_location,
            uav=uav,
            uav_fp=uav_fp,
            uav_fp_half="first-half",
        )
        uav.waypoints += _gen_horizontal_curve_waypoints(
            airplane_id=uav.ID,
            prev_airport=prev_airliner_airport_location,
            curr_airport=uav_airport_location,
            next_airport=next_airliner_airport_location,
            altitude_km=uav_fp.REFUELING_ALTITUDE_KM,
            turning_radius_km=uav_fp.TURNING_RADIUS_KM,
            DIRECT_APPROACH_SPEED_KMPH=uav_fp.CRUISE_SPEED_KMPH,
        )
        uav.waypoints += _generate_uav_waypoints(
            airport_A=next_airliner_airport_location,
            airport_B=uav_airport_location,
            uav=uav,
            uav_fp=uav_fp,
            uav_fp_half="second-half",
        )

    uav.waypoints[0].LOCATION.TAG = f"{uav.ID}-first-point"


def get_uav_on_airliner_point(
    airliner_fp: FlightPath,
    uav: Uav,
    kind: Literal["docking", "undocking"],
) -> Location:
    point = deepcopy(
        uav.get_tagged_waypoint(
            location_tag=f"{uav.ID}-on-airliner-{kind}-point"
        ).LOCATION
    )
    point.ALTITUDE_KM = airliner_fp.CRUISE_ALTITUDE_KM
    return point


def provision_airliner_from_flight_path(
    airliner: Airliner,
    airliner_fp: FlightPath,
    uavs: Dict[AIRPORT_CODE_TYPE, Dict[AirplaneId, Uav]],
    uav_fps: Dict[AIRPORT_CODE_TYPE, Dict[AirplaneId, UavFlightPath]],
) -> None:
    for i in range(len(airliner_fp.AIRPORT_LOCATIONS) - 1):
        prev_airport = airliner_fp.AIRPORT_LOCATIONS[i]
        next_airport = airliner_fp.AIRPORT_LOCATIONS[i + 1]

        if i == 0:
            # From first airport...

            airliner.location = prev_airport

            airliner.waypoints += _gen_takeoff_or_landing_waypoints(
                airplane_id=airliner.ID,
                takeoff_or_landing="TAKEOFF",
                airport_location=prev_airport,
                eventual_point=next_airport.xy_coords,
                flight_path=airliner_fp,
            )

            airliner.set_heading(airliner.waypoints[0])

        if i < len(airliner_fp.AIRPORT_CODES) - 2:
            # Between any two airports...

            # Cruise

            def provision_airliner_docking(
                service_side: Literal["to-airport", "from-airport"]
            ) -> None:
                airport_uavs = list(uavs[next_airport.CODE][service_side].values())
                airport_uav_fps = list(
                    uav_fps[next_airport.CODE][service_side].values()
                )

                for j in range(len(airport_uavs) + 1):
                    if j < len(airport_uavs):
                        uav = airport_uavs[j]
                        uav_fp = airport_uav_fps[j]
                        uav_on_airliner_docking_point = get_uav_on_airliner_point(
                            airliner_fp, uav, kind="docking"
                        )

                    if j == 0 and service_side == "to-airport":
                        start_location = Location(
                            *_intermediate_point_between(
                                (
                                    uav_on_airliner_docking_point
                                    if len(airport_uavs) > 0
                                    else curve_waypoints[0].LOCATION
                                ).xy_coords,
                                prev_airport.xy_coords,
                                airliner_fp.SPEED_CHANGE_DISTANCE_KM,
                            ),
                            ALTITUDE_KM=airliner_fp.CRUISE_ALTITUDE_KM,
                        )
                        start_speed_kmph = airliner_fp.CRUISE_SPEED_KMPH
                    elif len(airport_uavs) > 0:
                        prev_uav = airport_uavs[j - 1]
                        prev_uav_fp = airport_uav_fps[j - 1]
                        prev_uav_on_airliner_undocking_point = (
                            get_uav_on_airliner_point(
                                airliner_fp, uav=prev_uav, kind="undocking"
                            )
                        )
                        start_location = prev_uav_on_airliner_undocking_point
                        start_speed_kmph = prev_uav_fp.CRUISE_SPEED_KMPH
                    else:
                        start_location = curve_waypoints[-1].LOCATION
                        start_speed_kmph = 300  # TODO

                    if j < len(airport_uavs):
                        end_location = uav_on_airliner_docking_point
                        end_speed_kmph = uav_fp.CRUISE_SPEED_KMPH
                    elif service_side == "from-airport":
                        end_location = Location(
                            *_intermediate_point_between(
                                (
                                    prev_uav_on_airliner_undocking_point
                                    if len(airport_uavs) > 0
                                    else curve_waypoints[-1].LOCATION
                                ).xy_coords,
                                airliner_fp.AIRPORT_LOCATIONS[i + 2].xy_coords,
                                airliner_fp.SPEED_CHANGE_DISTANCE_KM,
                            ),
                            ALTITUDE_KM=airliner_fp.CRUISE_ALTITUDE_KM,
                        )
                        end_speed_kmph = airliner_fp.CRUISE_SPEED_KMPH
                    elif len(airport_uavs) == 0:
                        end_location = curve_waypoints[0].LOCATION
                        end_speed_kmph = 300  # TODO

                    if (
                        j == 0
                        and service_side == "to-airport"
                        or j == len(airport_uavs)
                        and service_side == "from-airport"
                    ):
                        airliner.waypoints += _gen_speed_change_waypoints(
                            start_location=start_location,
                            start_speed_kmph=start_speed_kmph,
                            end_location=end_location,
                            end_speed_kmph=end_speed_kmph,
                        )
                    if j < len(airport_uavs):
                        airliner.waypoints.append(
                            Waypoint(
                                uav_on_airliner_docking_point,
                                DIRECT_APPROACH_SPEED_KMPH=uav_fp.CRUISE_SPEED_KMPH,
                            )
                        )
                        airliner.waypoints.append(
                            Waypoint(
                                get_uav_on_airliner_point(
                                    airliner_fp, uav=uav, kind="undocking"
                                ),
                                DIRECT_APPROACH_SPEED_KMPH=uav_fp.CRUISE_SPEED_KMPH,
                            )
                        )

            curve_waypoints = _gen_horizontal_curve_waypoints(
                airplane_id=airliner.ID,
                prev_airport=airliner_fp.AIRPORT_LOCATIONS[i],
                curr_airport=airliner_fp.AIRPORT_LOCATIONS[i + 1],
                next_airport=airliner_fp.AIRPORT_LOCATIONS[i + 2],
                altitude_km=airliner_fp.CRUISE_ALTITUDE_KM,
                turning_radius_km=airliner_fp.TURNING_RADIUS_KM,
                DIRECT_APPROACH_SPEED_KMPH=300,  # TODO
            )
            provision_airliner_docking(service_side="to-airport")
            airliner.waypoints += curve_waypoints
            provision_airliner_docking(service_side="from-airport")

        if i == len(airliner_fp.AIRPORT_CODES) - 2:
            # To last airport...

            airliner.waypoints += _gen_takeoff_or_landing_waypoints(
                airplane_id=airliner.ID,
                takeoff_or_landing="LANDING",
                airport_location=next_airport,
                eventual_point=prev_airport.xy_coords,
                flight_path=airliner_fp,
            )


def delay_uavs(
    uavs: Dict[AIRPORT_CODE_TYPE, Dict[AirplaneId, Uav]], airliner: Airliner
) -> None:
    for airport_uavs in uavs.values():
        for uav in airport_uavs.values():
            uav_travel_duration_to_docking_point = (
                uav.get_travel_durations_to_tagged_waypoints()[
                    f"{uav.ID}-on-airliner-docking-point"
                ]
            )
            airliner_travel_duration_to_docking_point = (
                airliner.get_travel_durations_to_tagged_waypoints()[
                    f"{uav.ID}-on-airliner-docking-point"
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


def viz_airplane_paths(airplanes: List[Airplane], markers: bool = False) -> None:
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
        locations = [
            loc.xyz_coords
            for loc in [airplane.location] + [wp.LOCATION for wp in airplane.waypoints]
        ]
        speeds_kmph = [wp.DIRECT_APPROACH_SPEED_KMPH for wp in airplane.waypoints]
        pair_segments = list(zip(locations[1:], locations[:-1]))
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
