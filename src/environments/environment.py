"""
Notes:
    Environments themselves are not stateful; emulators or their corresponding deployment interfaces
        are.
"""

import dataclasses
import datetime as dt
import time
from copy import deepcopy
from typing import Optional, Union

from src.agents import BaseAgent
from src.emulators import EvTaxisEmulator
from src.deployment_interfaces.agent_interface import AgentInterface
from src.deployment_interfaces.ev_taxis_interface import EvTaxisInterface
from src.modeling_objects import AgentAction, EnvironmentState
from src.projects import PROJECT_TYPE
from src.utils.utils import now


@dataclasses.dataclass(init=False)
class EnvironmentConfig:
    TIME_STEP: Union[dt.timedelta, None] = dataclasses.field(init=False)
    """The length of time to use when stepping from one environment iteration to the next."""
    DELAY_TIME_STEP: Union[dt.timedelta, None] = dataclasses.field(init=False)
    """The minimum length of real time to pause when stepping from one environment iteration to the
    next, which is useful in a real-time deployment setting.
    """
    START_TIMESTAMP: Union[dt.datetime, None] = dataclasses.field(init=False)
    """The timestamp to use for the first environment iteration."""
    SKIP_TIMEDELTA: dt.timedelta = dt.timedelta(0)
    END_TIMESTAMP: Optional[dt.datetime] = dataclasses.field(init=False)
    """The timestamp to use for the last environment iteration, if any."""

    def __init__(self, **kwargs):
        """
        Not all environments require a ``TIME_STEP`` or ``DELAY_TIME_STEP`` (e.g., the
        ``EvTaxisEmulatorEnvironment``), in which case they they will be ignored if present.

        Setting the ``TIME_STEP`` to None or omitting it from the ``kwargs`` results in the
        environment only running one iteration.

        Setting the ``DELAY_TIME_STEP`` to None or omitting it from the ``kwargs`` results in it
        automatically being set to the ``TIME_STEP``.

        Setting the ``START_TIMESTAMP`` to None results in it automatically being determined from
        the emulator from its data, when instantiating the environment, if the environment's
        ``ev_taxis_emulator_or_interface`` attribute is an emulator.
        Omitting the ``START_TIMESTAMP`` from the ``kwargs`` is different to setting it to None, and
        results in it being set to the current datetime ('right now'), which is useful in a
        real-time deployment setting.

        The ``END_TIMESTAMP`` is optional, and may be set to None or omitted from the ``kwargs``.
        """

        for k, v in kwargs.items():
            setattr(self, k, v)

        if "TIME_STEP" not in kwargs.keys():
            self.TIME_STEP = None
        if "DELAY_TIME_STEP" not in kwargs.keys():
            self.DELAY_TIME_STEP = None
        if self.DELAY_TIME_STEP is None:
            self.DELAY_TIME_STEP = self.TIME_STEP
        else:
            assert self.TIME_STEP is not None
        if "START_TIMESTAMP" not in kwargs.keys():
            self.START_TIMESTAMP = now
        if "END_TIMESTAMP" not in kwargs.keys():
            self.END_TIMESTAMP = None


@dataclasses.dataclass
class BaseEnvironment(EnvironmentConfig):
    """An environment for EV taxis."""

    ENVIRONMENT_CONFIG: EnvironmentConfig
    ev_taxis_emulator_or_interface: Union[EvTaxisEmulator, EvTaxisInterface]
    AGENT_OR_INTERFACE: Union[BaseAgent, AgentInterface, None] = None
    PROJECT: Union[PROJECT_TYPE, None] = None

    # The following attributes are instantiated by `__post_init__`, in part using the
    #     `ENVIRONMENT_CONFIG`, and their type hints overwrite those of the same attributes
    #     inherited from ``EnvironmentConfig``:
    TIME_STEP: dt.timedelta = dataclasses.field(init=False)
    DELAY_TIME_STEP: Union[dt.timedelta, None] = dataclasses.field(init=False)
    START_TIMESTAMP: dt.datetime = dataclasses.field(init=False)
    SKIP_TIMEDELTA: dt.timedelta = dataclasses.field(init=False)
    END_TIMESTAMP: Optional[dt.datetime] = dataclasses.field(init=False)

    def __post_init__(self):
        self.TIME_STEP = self.ENVIRONMENT_CONFIG.TIME_STEP
        self.DELAY_TIME_STEP = self.ENVIRONMENT_CONFIG.DELAY_TIME_STEP

        self.START_TIMESTAMP = self.ENVIRONMENT_CONFIG.START_TIMESTAMP
        # If the environment's ``ev_taxis_emulator_or_interface`` is an ``EvTaxisInterface``, which
        #     does not have a start timestamp, as opposed to an emulator, then the environment's
        #     ``START_TIMESTAMP`` must not be None:
        if isinstance(self.ev_taxis_emulator_or_interface, EvTaxisInterface):
            assert self.START_TIMESTAMP is not None
        # Otherwise, if the environment's ``START_TIMESTAMP`` is None, set it to the emulator's
        #     ``START_TIMESTAMP``:
        if self.START_TIMESTAMP is None:
            self.START_TIMESTAMP = self.ev_taxis_emulator_or_interface.START_TIMESTAMP

        self.SKIP_TIMEDELTA = self.ENVIRONMENT_CONFIG.SKIP_TIMEDELTA

        self.END_TIMESTAMP = self.ENVIRONMENT_CONFIG.END_TIMESTAMP

        self.current_timestamp = deepcopy(self.START_TIMESTAMP)

    def run(self) -> None:
        print(f"{type(self).__name__} running...")

    def _get_state(self, timestamp: dt.datetime) -> EnvironmentState:
        """Get the EnvironmentState, in part by updating the EvTaxisEmulator's state and accessing
        its ``evs_state`` and ``charging_sites_state`` attributes.
        """

        self.ev_taxis_emulator_or_interface.update_state(
            timestamp=self.current_timestamp
        )
        return self.ev_taxis_emulator_or_interface.current_state

    def _perform_action(self, action: AgentAction) -> None:
        self.ev_taxis_emulator_or_interface.set_action(action)

    @property
    def reward(self) -> float:
        """For, e.g., training an agent (like ``SocThresholdsAgent``)."""
        return self.ev_taxis_emulator_or_interface.total_revenue


@dataclasses.dataclass
class Environment(BaseEnvironment):
    def run(self) -> None:
        super().run()

        while True:
            if self.END_TIMESTAMP is not None:
                if self.current_timestamp >= self.END_TIMESTAMP:
                    break
            iteration_start_time = time.time()
            self._run_iteration()
            if self.TIME_STEP is None:
                break
            if self.DELAY_TIME_STEP is not None:
                iteration_time_elapsed = time.time() - iteration_start_time
                sleep_time = max(
                    self.DELAY_TIME_STEP.total_seconds() - iteration_time_elapsed, 0
                )
                time.sleep(sleep_time)

    def _run_iteration(self) -> None:
        # NOTE: Set a breakpoint here to debug iterations.
        print(
            f"current_timestamp of the {type(self).__name__}: {self.current_timestamp}. "
            f"Waiting for DELAY_TIME_STEP = {self.DELAY_TIME_STEP}..."
        )
        state = self._get_state(timestamp=self.current_timestamp)
        if self.AGENT_OR_INTERFACE is not None:
            action = self.AGENT_OR_INTERFACE.action(
                timestamp=self.current_timestamp, environment_state=state
            )
            self._perform_action(action)
        if self.TIME_STEP is not None:
            self.current_timestamp += self.TIME_STEP
