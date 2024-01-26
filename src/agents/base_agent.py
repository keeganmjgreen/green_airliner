import abc
import datetime as dt

from src.modeling_objects import AgentAction, EnvironmentState


class BaseAgent(abc.ABC):
    @abc.abstractmethod
    def action(
        self, timestamp: dt.datetime, environment_state: EnvironmentState
    ) -> AgentAction:
        raise NotImplementedError
