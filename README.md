## 3D simulation

### Running via command line

Set `PYTHONPATH` to the repo root, e.g.:
```
export PYTHONPATH=/home/keegan_green/Dropbox/Documents/Projects/electric_airline/
```
Activate the Conda environment:
```
conda activate electric_airline
```
Run the 3D simulation:
```
python src/three_d_sim/study_runner.py --view=... --track-airplane-id=... --preset=...
```

### Different visualizations



#### Side views of airplanes

Airliner:

`python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=Airliner`

UAVs from PIT:
  - First UAV (leading up to PIT flyover):
    
    `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=PIT-UAV-0`
    
  - Second UAV (directly after PIT flyover):
    
    `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=PIT-UAV-1`

UAVs from DEN:
  - Leading up to DEN flyover:
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-0`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-1`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-2`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-3`
  - Directly after DEN flyover:
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-4`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-5`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-6`

#### "Bird's eye" (map) view of all airplanes

The following usage of `--view=map-view` shows all airplanes (airliner and UAVs) from above, zoomed out such that they are always visible. The airplane and UAVs' 3D models and elevations are scaled up, for illustrative purposes, such that they remain visible.

`python src/three_d_sim/study_runner.py --view=map-view --track-airplane-id=Airliner`

#### Airliner speed and SoC graphs

Realtime graphs of the airliner's speed and SoC over time are shown in the VPython browser tab.

Given this fact, the following usage of `--preset=record-graphs` is only useful when screen-recording them in order to generate the Manim video.

`python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=Airliner --preset=record-graphs`
