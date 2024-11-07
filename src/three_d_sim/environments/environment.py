"""
Notes:
    Environments themselves are not stateful; emulators or their corresponding deployment interfaces
        are.
"""

import dataclasses
import datetime as dt
import time
from typing import Optional, Union

from src.airplanes_simulator import AirplanesSimulator
from src.modeling_objects import AirplanesState
from src.utils.utils import get_interpolator_by_elapsed_time, timedelta_to_minutes


@dataclasses.dataclass
class BaseEnvironment:
    """An environment for EV taxis."""

    ev_taxis_emulator_or_interface: AirplanesSimulator

    # The following attributes are instantiated by `__post_init__`, in part using the
    #     `ENVIRONMENT_CONFIG`, and their type hints overwrite those of the same attributes
    #     inherited from ``EnvironmentConfig``:
    time_step: dt.timedelta
    delay_time_step: Union[dt.timedelta, None]
    skip_timedelta: dt.timedelta
    end_time: Optional[dt.timedelta]

    def __post_init__(self):
        self.current_time = dt.timedelta(0)

    def run(self) -> None:
        print(f"{type(self).__name__} running...")

    def _get_state(self) -> AirplanesState:
        """Update and return the AirplanesSimulator's state."""

        self.ev_taxis_emulator_or_interface.update_state(time=self.current_time)
        return self.ev_taxis_emulator_or_interface.current_state

    @property
    def reward(self) -> float:
        """For, e.g., training an agent (like ``SocThresholdsAgent``)."""
        return self.ev_taxis_emulator_or_interface.total_revenue


@dataclasses.dataclass
class Environment(BaseEnvironment):
    def run(self) -> None:
        super().run()

        while True:
            if self.end_time is not None:
                if self.current_time >= self.end_time:
                    break
            iteration_start_time = time.time()
            self._run_iteration()
            if self.time_step is None:
                break
            if self.delay_time_step is not None:
                iteration_time_elapsed = time.time() - iteration_start_time
                sleep_time = max(
                    self.delay_time_step.total_seconds() - iteration_time_elapsed, 0
                )
                time.sleep(sleep_time)

    def _run_iteration(self) -> None:
        # NOTE: Set a breakpoint here to debug iterations.
        print(
            f"{timedelta_to_minutes(self.current_time):.2f} minutes elapsed", end=";  "
        )
        self._get_state()
        if self.time_step is not None:
            time_step_interpolator = get_interpolator_by_elapsed_time(self.time_step)
            time_step = dt.timedelta(
                seconds=float(
                    time_step_interpolator(timedelta_to_minutes(self.current_time))
                )
            )
            print(f"time_step: {time_step.total_seconds():.2f}", end=";  ")
            self.current_time += time_step
