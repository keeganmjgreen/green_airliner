This documentation assumes that you are using a Linux-based OS.

## 3D simulation

The 3D simulation is rendered via VPython in a browser tab. Unless `--view=map-view`, the camera follows the airplane specified by `--track-airplane-id`. The browser view consists also of some text-based readouts for the airplanes, and realtime graphs of the airliner's speed and SoC over time.

The browser tab opens in your system's default browser. With the assumption that this is Google Chrome, the program firstly and automatically opens a new "guest" Chrome window in which this new browser tab will be opened. The program will stop (and the 3D rendering will freeze) at a certain time for each `--track-airplane-id`, but it can be stopped early when running from the command line by pressing `Ctrl`+`C` therein. After, the "guest" Chrome window can be closed. 

The 3D simulation is run by `src/three_d_sim/study_runner.py` (the program's entry point).

### Running via command line

1. Set `PYTHONPATH` to the repo root, e.g.:
    
    `export PYTHONPATH=/home/keegan_green/Dropbox/Documents/Projects/electric_airline/`
    
2. Activate the Conda environment:
    
    `conda activate electric_airline`
    
3. Run the 3D simulation:
    
    `python src/three_d_sim/study_runner.py --view=... --track-airplane-id=... --preset=...`

For options for the `--view`, `--track-airplane-id`, and `--preset` command-line arguments, see the "Different visualizations" subsection.

Specifying ` --preset=record-airplanes-viz` records the 3D rendering and saves it to a `.avi` video file with a specific name. Because newer VPython no longer supports opening 3D renderings in standalone windows and the functionality to write the 3D rendering to a video file seems to no longer work, this is done by screen-recording region(s) of the screen whose coordinates are hard-coded in `study_runner.py`. While automatic, a consequence is not being able to use that screen region for other purposes during simulation/recording. An advantage over manual screen-recording, however, is that the recorded frame rate is fixed and synced with the simulation, and thus unaffected by any lags in running the program.

`--preset=record-graphs` is similar, but records both the airliner's speed graph and SoC graph to separate video files.

### Different 3D visualizations

#### Side views of airplanes

Airliner:

`python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=Airliner --preset=record-airplanes-viz`

UAVs from PIT:
  - First UAV (leading up to PIT flyover):
    
    `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=PIT-UAV-0 --preset=record-airplanes-viz`
    
  - Second UAV (directly after PIT flyover):
    
    `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=PIT-UAV-1 --preset=record-airplanes-viz`

UAVs from DEN:
  - Leading up to DEN flyover:
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-0 --preset=record-airplanes-viz`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-1 --preset=record-airplanes-viz`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-2 --preset=record-airplanes-viz`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-3 --preset=record-airplanes-viz`
  - Directly after DEN flyover:
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-4 --preset=record-airplanes-viz`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-5 --preset=record-airplanes-viz`
    - `python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=DEN-UAV-6 --preset=record-airplanes-viz`

#### "Bird's eye" (map) view of all airplanes

The following usage of `--view=map-view` shows all airplanes (airliner and UAVs) from above, zoomed out such that they are always visible. The airplane and UAVs' 3D models and elevations are scaled up, for illustrative purposes, such that they remain visible.

`python src/three_d_sim/study_runner.py --view=map-view --track-airplane-id=Airliner --preset=record-airplanes-viz`

#### Airliner speed and SoC graphs

The airliner's speed and SoC graphs are already shown in the browser tab. Given this fact, the following usage of `--preset=record-graphs` is only useful when screen-recording them in order to generate the Manim video.

`python src/three_d_sim/study_runner.py --view=side-view --track-airplane-id=Airliner --preset=record-graphs`

### Generating the video presentation using Manim

`manim_video.py`

#### Combining 3D visualizations and airliner graphs into a composite video

- Low quality: `conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -ql /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/Video.mp4`
- Medium quality: `conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qm /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/Video.mp4`
- High quality: `conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qH /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/Video.mp4`

#### Generating the presentation's intro

- Low quality: `conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -ql /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Intro && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/Intro.mp4`
- Medium quality: `conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qm /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Intro && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/Intro.mp4`
- High quality: `conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qH /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Intro && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/Intro.mp4`

#### Combining the intro and composite video into the video presentation

- Low quality: `conda activate electric_airline && cd /home/keegan_green/Dropbox/Documents/Projects/electric_airline/ && python combine_manim_videos.py --work-dir=/home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/ && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/final.mp4`
- Medium quality: `conda activate electric_airline && cd /home/keegan_green/Dropbox/Documents/Projects/electric_airline/ && python combine_manim_videos.py --work-dir=/home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/ && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/final.mp4`
- High quality: `conda activate electric_airline && cd /home/keegan_green/Dropbox/Documents/Projects/electric_airline/ && python combine_manim_videos.py --work-dir=/home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/ && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/final.mp4`
