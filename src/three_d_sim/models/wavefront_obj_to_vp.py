import numpy as np
import vpython as vp

from src.modeling_objects import ModelConfig
from src.utils.utils import M_PER_KM

MODELS_DIR = "src/three_d_sim/models/"


def simple_wavefront_obj_to_vp(
    model_config: ModelConfig, **vp_obj_kwargs
) -> vp.compound:
    with open(MODELS_DIR + model_config.model_subpath, "r") as f:
        lines = f.readlines()

    vertices = []
    faces = []
    for line in lines:
        if line[0] == "#" or line == "\n":
            continue
        elements = line[:-1].split(" ")
        if elements[0] in ["vn", "v"]:
            vec = np.array([float(e) for e in elements[1:]])
            vec = vec.dot(model_config.rotation_matrix)
            if elements[0] == "vn":
                vn = vp.vec(*vec)
            elif elements[0] == "v":
                vertices.append(vp.vertex(pos=vp.vec(*vec), normal=vn))
        elif elements[0] == "f":
            faces.append(
                vp.triangle(
                    vs=[vertices[int(e.split("//")[0]) - 1] for e in elements[1:]]
                )
            )
        else:
            raise NotImplementedError

    vp_obj = vp.compound(faces, **vp_obj_kwargs)
    # ^ Requires manually changing:
	#     obj._axis.value = obj._size._x*norm(obj._axis)
    # to:
    #     obj._axis.value = norm(obj._axis)*obj._size._x
    # in `~/miniconda3/envs/green_airliner/lib/python3.12/site-packages/vpython/vpython.py`.

    if model_config.length_m is not None:
        vp_obj.size *= model_config.length_m / M_PER_KM / vp_obj.size.x

    return vp_obj


if __name__ == "__main__":
    vp_obj = simple_wavefront_obj_to_vp(
        # "airliner/airbus-a320--1/Airbus_A320__Before_Scale_Up_-meshlabjs-simplified.obj"
        "uav/cessna-208-1.snapshot.2/Cessna_208-meshlab.obj"
    )
