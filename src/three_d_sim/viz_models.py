import dataclasses
from typing import Optional

import numpy as np


@dataclasses.dataclass
class ModelConfig:
    model_subpath: str
    rotation_matrix: Optional[np.ndarray] = None
    TRANSLATION_VECTOR: Optional[np.ndarray] = None
    length_m: float = None

    def __post_init__(self):
        if self.rotation_matrix is None:
            self.rotation_matrix = np.eye(3)
        if self.TRANSLATION_VECTOR is None:
            self.TRANSLATION_VECTOR = np.zeros(3)


a320 = ModelConfig(
    model_subpath="airliner/airbus-a320--1/Airbus_A320__Before_Scale_Up_-meshlabjs-simplified.obj",
    rotation_matrix=np.array(
        [
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 0],
        ]
    ),
    length_m=37.57,
    # ^ https://aircraft.airbus.com/en/aircraft/a320-the-most-successful-aircraft-family-ever/a320ceo
)

cessna = ModelConfig(
    model_subpath="uav/cessna-208-1.snapshot.2/Cessna_208-meshlab.obj",
    rotation_matrix=np.array(
        [
            [-1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
        ]
    ),
    length_m=11.45,
    # ^ https://cessna.txtav.com/en/turboprop/caravan
    #     https://cessna.txtav.com/-/media/cessna/files/caravan/caravan/caravan_short_productcard.ashx
)

airliner_model_lookup = {
    "a320": a320,
}
uav_model_lookup = {
    "cessna": cessna,
}
