"""
Notes:
    Environments themselves are not stateful; emulators or their corresponding deployment interfaces
        are.
"""

import dataclasses
import datetime as dt
import time
from typing import List, Optional

import scipy as sp

from src.airplanes_simulator import AirplanesSimulator
from src.modeling_objects import AirplanesState
from src.utils.utils import timedelta_to_minutes
from src.three_d_sim.config_model import Ratepoint, Timepoint


def get_interpolator_by_elapsed_time(points: List[Timepoint]):
    def interpolator(elapsed_mins: float):
        _interpolator = sp.interpolate.interp1d(
            x=[p.elapsed_mins for p in points],
            y=[p.value for p in points],
            bounds_error=False,
            fill_value=(points[0].value, points[-1].value),
        )
        y = _interpolator(elapsed_mins)
        return float(y)

    return interpolator


@dataclasses.dataclass
class BaseEnvironment:
    """An environment for EV taxis."""

    ev_taxis_emulator_or_interface: AirplanesSimulator

    # The following attributes are instantiated by `__post_init__`, in part using the
    #     `ENVIRONMENT_CONFIG`, and their type hints overwrite those of the same attributes
    #     inherited from ``EnvironmentConfig``:
    ratepoints: List[Ratepoint]
    time_step_multiplier: float = 1.0
    skip_timedelta: dt.timedelta = dt.timedelta(0)
    end_time: Optional[dt.timedelta] = None

    def __post_init__(self):
        self.current_time = dt.timedelta(0)

    def run(self) -> None:
        print(f"{type(self).__name__} running...")

    def _get_state(self) -> AirplanesState:
        """Update and return the AirplanesSimulator's state."""

        self.ev_taxis_emulator_or_interface.update_state(time=self.current_time)
        return self.ev_taxis_emulator_or_interface.current_state


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
            if self.ratepoints is None:
                break

    def _run_iteration(self) -> None:
        # NOTE: Set a breakpoint here to debug iterations.
        print(f"{timedelta_to_minutes(self.current_time):.2f} minutes elapsed")
        self._get_state()
        if self.ratepoints is not None:
            ratepoints_interpolator = get_interpolator_by_elapsed_time(self.ratepoints)
            time_step_s = ratepoints_interpolator(timedelta_to_minutes(self.current_time))
            print(f"{time_step_s = }")
            self.current_time += dt.timedelta(seconds=(time_step_s * self.time_step_multiplier))
