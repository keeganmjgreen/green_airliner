import dataclasses
import datetime as dt
from copy import deepcopy

from src.modeling_objects import Airliner, AirplanesState


@dataclasses.dataclass
class AirplanesSimulator:
    """Emulator/simulator of EV taxi operations, including changes in EV taxis' trip assignments,
    locations, and SoCs over time.

    The emulator keeps track of these as well as trip distance and revenue.
    It assigns EV taxis to fulfill trips as they are requested by taxi customers, updates the
    locations and  (discharging) SoCs of those EVs that are in motion, and updates the SoCs of those
    EVs that are charging at a charge point's connector at a charging site.
    """

    initial_state: AirplanesState
    current_state: AirplanesState = dataclasses.field(init=False)
    current_time: dt.timedelta = dataclasses.field(init=False)

    def __post_init__(self):
        self.current_time = dt.timedelta(0)
        self.current_state = deepcopy(self.initial_state)

    def update_state(self, time: dt.timedelta) -> None:
        """Update the current AirplanesState by first updating the current timestamp
        (BaseEmulator.update_state), then by updating airplanes' locations and SoCs.
        """

        prev_time = deepcopy(self.current_time)

        assert time >= self.current_time
        self.current_time = time

        self._update_evs_locations_and_energy_consumption(prev_time)
        self._update_evs_refueling(prev_time)

    def _update_evs_locations_and_energy_consumption(
        self, prev_time: dt.timedelta
    ) -> None:
        """Update the locations and (discharging) SoCs of EVs that are in motion."""

        for ev in self.current_state.airplanes.values():
            intermediate_time = deepcopy(prev_time)

            for i, waypoint in enumerate(ev.waypoints):
                ev.set_heading(to_waypoint=waypoint)

                if waypoint.TIME_INTO_SIMULATION > intermediate_time:
                    if waypoint.TIME_INTO_SIMULATION < self.current_time:
                        intermediate_time = waypoint.TIME_INTO_SIMULATION
                    else:
                        break

                waypoint_direct_arrival_time = (
                    waypoint.get_direct_arrival_time(
                        origin=ev.location, start_time=intermediate_time
                    )
                )
                if waypoint_direct_arrival_time < self.current_time:
                    # If the EV can reach the waypoint before current_timestamp, set the EV's
                    #     location to the waypoint's location:
                    ev.move_to_location(waypoint.LOCATION)
                    tag = waypoint.LOCATION.TAG
                    if tag is not None:
                        print(f"{ev.id} has reached waypoint with location tag {tag}.")
                        if "_on_airliner_docking_point" in tag:
                            self.current_state.airplanes[
                                "Airliner"
                            ].docked_uav = tag.removesuffix("_on_airliner_docking_point")
                        elif "_on_airliner_undocking_point" in tag:
                            self.current_state.airplanes["Airliner"].docked_uav = None
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
                                self.current_time - intermediate_time
                            ),
                        )
                    )
                    break
                intermediate_time = waypoint_direct_arrival_time

            # Clean up by removing waypoints that were marked for removal:
            ev.waypoints = [wp for wp in ev.waypoints if wp is not None]

    def _update_evs_refueling(self, prev_time: dt.timedelta) -> None:
        """Update the SoCs of EVs that are charging (at a charge point's connector at a charging
        site).
        """

        for ev in self.current_state.airplanes.values():
            if type(ev) is Airliner and ev.docked_uav:
                airliner = ev
                uav = self.current_state.airplanes[ev.docked_uav]

                charging_power_kw = min(
                    ev.refueling_rate_kW,
                    uav.refueling_rate_kW,
                )
                duration = self.current_time - prev_time

                if airliner.energy_level_pc < airliner.energy_level_pc_bounds[1]:
                    airliner.charge_for_duration(charging_power_kw, duration)
                    uav.charge_for_duration(
                        -charging_power_kw, duration, refueling_energy_level=True
                    )
