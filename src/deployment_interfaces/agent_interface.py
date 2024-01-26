"""
The ``AgentInterface`` is unused but could be used with the ``Environment``, instead of using the
``EvTaxisEmulatorEnvironment``, for the EV Taxis Emulator component of the deployment.
Doing so would not require the NiFi RA that is used with the deployed
``EvTaxisEmulatorEnvironment``.
"""

import datetime as dt

from src.modeling_objects import AgentAction, EnvironmentState
from src.agents import BaseAgent


class AgentInterface(BaseAgent):
    """A stand-in for an agent deployed elsewhere.

    Can be used in an ``Environment``, with the ``EvTaxisEmulator``, to get the agent's action.
    """

    def action(
        self, timestamp: dt.datetime, environment_state: EnvironmentState
    ) -> AgentAction:
        self.upload_state_to_db(environment_state)
        ...  # TODO
        raise NotImplementedError

    @staticmethod
    def upload_state_to_db(state: EnvironmentState):
        raise NotImplementedError  # TODO
