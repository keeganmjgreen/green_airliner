"""Classes for constructing and representing an Optimizer's dispatch.

The format is designed to be universal among optimizers; not specific to the EV Taxis Optimizer.
"""

from __future__ import annotations

import dataclasses
from copy import deepcopy
from typing import Any, Dict, List, Literal, Type, Union


class RecommendedCommand:
    def to_json(self) -> Dict[str, Any]:
        return {
            "commandType": type(self).__name__,
            "commandFields": {
                f.name: getattr(self, f.name) for f in dataclasses.fields(self)
            },
        }

    @staticmethod
    def from_json(json_recommended_command: Dict[str, Any]) -> RecommendedCommand:
        recommended_command_class = RECOMMENDED_COMMAND_CLASSES[
            json_recommended_command["commandType"]
        ]
        return recommended_command_class(**json_recommended_command["commandFields"])


@dataclasses.dataclass
class ChargingRateLimit(RecommendedCommand):
    chargingRateUnit: Literal["power_kW", "power_A"]
    chargingRateLimit: float


@dataclasses.dataclass
class EvChargingTransactionState(RecommendedCommand):
    transactionState: Literal["start", "stop"]


@dataclasses.dataclass
class ChargingSiteRecommendation(RecommendedCommand):
    chargingSiteId: Union[str, None]


RECOMMENDED_COMMAND_CLASSES = {
    "ChargingRateLimit": ChargingRateLimit,
    "EvChargingTransactionState": EvChargingTransactionState,
    "ChargingSiteRecommendation": ChargingSiteRecommendation,
}


@dataclasses.dataclass
class AssetAction:
    assetType: Literal["chargePoint", "vehicle"]
    assetId: str
    priority: Union[int, None]
    recommendedCommands: List[RecommendedCommand]

    def to_json(self) -> Dict[str, Any]:
        return {
            "assetType": self.assetType,
            "assetId": self.assetId,
            "priority": self.priority,
            "recommendedCommands": [x.to_json() for x in self.recommendedCommands],
        }

    @classmethod
    def from_json(cls, json_asset_action: Dict[str, Any]) -> AssetAction:
        _asset_action = deepcopy(json_asset_action)
        _asset_action["recommendedCommands"] = [
            RecommendedCommand.from_json(json_rc)
            for json_rc in _asset_action["recommendedCommands"]
        ]
        return cls(**_asset_action)

    def contains_recommended_command_type(
        self, recommended_command_type: Type[RecommendedCommand]
    ) -> bool:
        """Return True if at least one of the asset action's recommended commands are of the given
        type, False otherwise.
        """
        return any(
            isinstance(rc, recommended_command_type) for rc in self.recommendedCommands
        )

    def get_1x_recommended_command_type(
        self, recommended_command_type: Type[RecommendedCommand]
    ) -> bool:
        """Return exactly one of the asset action's recommended commands that is of the given type.
        Fails if there are multiple recommended commands of the given type.
        """
        recommended_commands = [
            rc
            for rc in self.recommendedCommands
            if isinstance(rc, recommended_command_type)
        ]
        assert len(recommended_commands) == 1
        return recommended_commands[0]


@dataclasses.dataclass
class OptimizerDispatch:
    recommendedActions: List[AssetAction]
    strategyType: Literal["smart", "manual"]

    def to_json(self) -> Dict[str, Any]:
        return {
            "recommendedActions": [x.to_json() for x in self.recommendedActions],
            "strategyType": self.strategyType,
        }
