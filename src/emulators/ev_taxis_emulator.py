from __future__ import annotations

import dataclasses
import datetime as dt
from copy import deepcopy

from src.modeling_objects import Airliner, EnvironmentState

from .base_emulator import BaseEmulator


@dataclasses.dataclass
class EvTaxisEmulator(BaseEmulator):
    """Emulator/simulator of EV taxi operations, including changes in EV taxis' trip assignments,
    locations, and SoCs over time.

    The emulator keeps track of these as well as trip distance and revenue.
    It assigns EV taxis to fulfill trips as they are requested by taxi customers, updates the
    locations and  (discharging) SoCs of those EVs that are in motion, and updates the SoCs of those
    EVs that are charging at a charge point's connector at a charging site.

    Notes:
        If the ``START_TIMESTAMP`` is None or not specified, it will be set to the earliest
        requested timestamp in the ``TRIPS_DEMAND_DATASET``.
        If the ``TRIPS_DEMAND_DATASET`` does not have a "distance_km" column, it will be determined
            as the from the trip origins and destinations for ended trips.
        If the ``TRIPS_DEMAND_DATASET`` does not have a "revenue" column, it will be determined by
            the ``determine_revenue`` method of the ``TRIP_CLASS`` for ended trips.
    """

    START_STATE: EnvironmentState
    # TODO: Implement optional `.END_TIMESTAMP`.

    APPROX_MAX_TIME_STEP: dt.timedelta = dataclasses.field(
        init=False, default=dt.timedelta(minutes=10)
    )  # Somewhat arbitrary.
    """See docstring of method ``update_state``."""

    current_state: EnvironmentState = dataclasses.field(init=False)

    def __post_init__(self):
        # If the `START_TIMESTAMP` is None or not specified, set it to the earliest requested
        #     timestamp in the `TRIPS_DEMAND_DATASET`:
        if self.START_TIMESTAMP is None:
            self.START_TIMESTAMP = (
                self._trips_dataset["requested_timestamp"].min().to_pydatetime()
            )

        super().__post_init__()

    def update_state(self, timestamp: dt.datetime) -> None:
        """Update the current EnvironmentState by first updating the current timestamp
        (BaseEmulator.update_state), then by updating EVs' trip assignments, locations, and SoCs.

        NOTE: Although each of the ``self._update_...`` methods operates in continuous-time (as
        opposed to discrete-time) between iterations of ``self.update_state`` (from prev_timestamp
        to current_timestamp), each of those methods operate on ``self.current_state`` sequentially,
        meaning that too long of a time step from ``self.current_timestamp`` to ``timestamp`` will
        cause less-than-realistic simulated behavior (see ``self.APPROX_MAX_TIME_STEP``).
        EVs' trip assignments are processed before their location changes and SoC changes; trip
        assignments depend on EVs' locations and availabilities, but those are processed after.

        Todos:
            Make the aforementioned ``self._update_...`` methods's operations on
            ``self.current_state`` concurrent.
        """

        if timestamp - self.current_timestamp >= self.APPROX_MAX_TIME_STEP:
            raise Exception(
                f"{type(self).__name__}: Time step longer than `self.APPROX_MAX_TIME_STEP`, which "
                "may cause less-than-realistic simulated behavior."
            )

        prev_timestamp = deepcopy(self.current_timestamp)
        super().update_state(timestamp)

        self._update_evs_locations_and_discharging_socs(prev_timestamp)
        self._update_evs_charging_socs(prev_timestamp)

    def _update_evs_locations_and_discharging_socs(
        self, prev_timestamp: dt.datetime
    ) -> None:
        """Update the locations and (discharging) SoCs of EVs that are in motion."""

        for ev in self.current_state.evs_state.values():
            intermediate_timestamp = deepcopy(prev_timestamp)

            for i, waypoint in enumerate(ev.waypoints):
                ev.set_heading(to_waypoint=waypoint)

                waypoint_timestamp_into_simulation = (
                    self.START_TIMESTAMP + waypoint.TIME_INTO_SIMULATION
                )
                if waypoint_timestamp_into_simulation > intermediate_timestamp:
                    if waypoint_timestamp_into_simulation < self.current_timestamp:
                        intermediate_timestamp = waypoint_timestamp_into_simulation
                    else:
                        break

                waypoint_direct_arrival_timestamp = (
                    waypoint.get_direct_arrival_timestamp(
                        origin=ev.location, start_timestamp=intermediate_timestamp
                    )
                )
                if waypoint_direct_arrival_timestamp < self.current_timestamp:
                    # If the EV can reach the waypoint before current_timestamp, set the EV's
                    #     location to the waypoint's location:
                    ev.move_to_location(waypoint.LOCATION)
                    tag = waypoint.LOCATION.TAG
                    if tag is not None:
                        print(f"{ev.ID} has reached waypoint with location tag {tag}.")
                        if "-on-airliner-docking-point" in tag:
                            self.current_state.evs_state[
                                "Airliner"
                            ].connector = tag.removesuffix("-on-airliner-docking-point")
                        elif "-on-airliner-undocking-point" in tag:
                            self.current_state.evs_state["Airliner"].connector = None
                    # 'Clear' the waypoint:
                    ev.waypoints[i] = None  # Marked to be removed from waypoints.
                else:
                    # Otherwise, set the EV's new location to be an en route location between its
                    #     old location and the waypoint's location based on how far it can travel
                    #     until current_timestamp:
                    ev.move_to_location(
                        waypoint.get_direct_en_route_location(
                            origin=ev.location,
                            duration_traveled_so_far=(
                                self.current_timestamp - intermediate_timestamp
                            ),
                        )
                    )
                    break
                intermediate_timestamp = waypoint_direct_arrival_timestamp

            # Clean up by removing waypoints that were marked for removal:
            ev.waypoints = [wp for wp in ev.waypoints if wp is not None]

    def _update_evs_charging_socs(self, prev_timestamp: dt.datetime) -> None:
        """Update the SoCs of EVs that are charging (at a charge point's connector at a charging
        site).
        """

        for ev in self.current_state.evs_state.values():
            if type(ev) is Airliner and ev.is_plugged_in:
                airliner = ev
                uav = self.current_state.evs_state[ev.connector]

                charging_power_kw = min(
                    ev.CHARGING_POWER_LIMIT_KW,
                    uav.CHARGING_POWER_LIMIT_KW,
                )
                duration = self.current_timestamp - prev_timestamp

                # TODO clip
                airliner.charge_for_duration(charging_power_kw, duration)
                uav.charge_for_duration(
                    -charging_power_kw, duration, refueling_soc=True
                )
