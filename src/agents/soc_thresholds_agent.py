# TODO: Training the SoC 'recharge' and 'charged' thresholds?

from __future__ import annotations

import dataclasses
import datetime as dt
from copy import deepcopy
from typing import Optional

import numpy as np

from src.modeling_objects import AgentAction, EnvironmentState, EvAction

from .base_agent import BaseAgent


@dataclasses.dataclass
class SocThresholdsAgent(BaseAgent):
    CURRENT_SOC_RECHARGE_THRES: float
    CURRENT_SOC_CHARGED_THRES: float
    # ANTICIPATED_SOC_RECHARGE_THRES: Optional[float] = None
    # ^ TODO: Change to energy thres or per EV?

    def __post_init__(self):
        assert self.CURRENT_SOC_RECHARGE_THRES < self.CURRENT_SOC_CHARGED_THRES

    def action(
        self, timestamp: dt.datetime, environment_state: EnvironmentState
    ) -> AgentAction:
        # TODO: Handle two drivers going to the same charging site with only one connector left?

        ev_actions = {}
        for ev in environment_state.evs_state.values():
            # TODO Break ties, i.e., sort EVs?
            if ev._trip is None and ev.connector is None:
                # If the EV is not assigned to a trip and not at a charge point:
                if ev.soc <= self.CURRENT_SOC_RECHARGE_THRES:
                    closest_available_charging_site = (
                        ev.location.get_closest_available_asset(
                            assets=environment_state.charging_sites_state
                        )
                    )
                    ev_actions[ev.ID] = EvAction(
                        waypoint_charging_site_id=closest_available_charging_site.ID
                    )
                else:
                    ev_actions[ev.ID] = EvAction(waypoint_charging_site_id=None)
            elif ev.connector is not None:
                # If the EV is at a charge point:
                if ev.soc >= self.CURRENT_SOC_CHARGED_THRES:
                    ev_actions[ev.ID] = EvAction(waypoint_charging_site_id=None)
                else:
                    ev_actions[ev.ID] = EvAction(
                        waypoint_charging_site_id=ev.connector.PARENT_CHARGING_SITE_ID
                    )
            else:
                # If the EV is assigned to a trip:
                ev_actions[ev.ID] = EvAction(waypoint_charging_site_id=None)

        return AgentAction(ev_actions=ev_actions)

    @classmethod
    def train(
        cls,
        environment: "Environment",
        current_soc_recharge_thres_range: range,
        current_soc_charged_thres_range: range,
    ):
        """Grid search..."""

        assert environment.AGENT_OR_INTERFACE is None

        reward_df = pd.DataFrame(
            index=current_soc_recharge_thres_range,
            columns=current_soc_charged_thres_range,
        )

        # For each (recharge threshold, charged threshold) pair from the given `range`s, run an EV
        #     taxis simulation (EvTaxisEmulator and SocThresholdsAgent) based on the given
        #     `environment` and record the resulting revenue in the reward_df:
        # TODO: Use itertools?
        for current_soc_recharge_thres in current_soc_recharge_thres_range:
            for current_soc_charged_thres in current_soc_charged_thres_range:
                if current_soc_recharge_thres >= current_soc_charged_thres:
                    continue
                tmp_environment = deepcopy(environment)
                environment.AGENT_OR_INTERFACE = cls(
                    CURRENT_SOC_RECHARGE_THRES=current_soc_recharge_thres,
                    CURRENT_SOC_CHARGE_THRES=current_soc_charged_thres,
                )
                environment.run()
                reward_df.loc[
                    current_soc_recharge_thres,
                    current_soc_charged_thres,
                ] = environment.reward

        # Select the pair of SoC thresholds that maximized revenue:
        current_soc_recharge_thres, current_soc_charged_thres = np.unravel_index(
            np.argmax(reward_df.to_numpy()), reward_df.shape
        )

    @classmethod
    def from_model_id(cls, model_id: str) -> SocThresholdsAgent:
        ...
