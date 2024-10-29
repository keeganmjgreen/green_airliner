from typing import Dict
import numpy as np

from modeling_objects import ModelConfig

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

models = [
    a320,
    cessna,
]
models_lookup: Dict[str, ModelConfig] = {x.__name__: x for x in models}
