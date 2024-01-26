import dataclasses
import datetime as dt
from typing import List

import pandas as pd

from src.emulators import EvTaxisEmulator
from src.modeling_objects import AgentAction, EnvironmentState

from .base_agent import BaseAgent


@dataclasses.dataclass
class OptimizingAgent(BaseAgent):
    OPTIMIZATION_HORIZON: dt.timedelta
    BLOCK_DURATION: dt.timedelta

    def action(
        self, timestamp: dt.datetime, environment_state: EnvironmentState
    ) -> AgentAction:
        def objective_func(actions: List[AgentAction]) -> float:
            assert environment_state.forecasted_trips is not None
            ev_taxis_emulator = EvTaxisEmulator(
                trip_dataset=pd.DataFrame(
                    [trip.__dict__ for trip in environment_state.forecasted_trips]
                ),
                start_timestamp=timestamp,
                start_state=environment_state.evs_state,
            )
            states = []
            for timestamp in self._get_horizon_timestamps():
                ev_taxis_emulator.set_next_action(action)
                ev_taxis_emulator.update_state(time_step=self.BLOCK_DURATION)
                states.append(ev_taxis_emulator.current_state)

        ...  # TODO
        raise NotImplementedError

    def _get_horizon_timestamps(
        self, horizon_start_timestamp: dt.datetime
    ) -> List[dt.datetime]:
        return pd.date_range(
            start=horizon_start_timestamp,
            end=(horizon_start_timestamp + self.OPTIMIZATION_HORIZON),
            freq=self.BLOCK_DURATION,
        )
