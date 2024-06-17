"""
conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -ql /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/Video.mp4
conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qm /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/Video.mp4
conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qH /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/Video.mp4
"""

import dataclasses
from pathlib import Path
from typing import Tuple

import cv2
from manim import *

from manim.mobject.text import text_mobject

text_mobject.TEXT_MOB_SCALE_FACTOR = 0.01
text_mobject.DEFAULT_LINE_SPACING_SCALE = 0.8

config.max_files_cached = 4000

N_15FPS_FRAMES = 10
FRAME_RATE = 15
W = 1920
H = 1080
PX_PER_UNIT = 135


@dataclasses.dataclass
class VideoFeed:
    fpath: Path
    scale: float
    pos: np.array

    def __post_init__(self):
        self.cap = cv2.VideoCapture(self.fpath)

    def add_to(self, scene: Scene):
        flag, frame = self.cap.read()
        if flag:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.image_mobject = ImageMobject(frame).scale(self.scale).move_to([*self.pos, 0])
            scene.add(self.image_mobject)
        else:
            self.image_mobject = None

    def remove_from(self, scene: Scene):
        if self.image_mobject is not None:
            scene.remove(self.image_mobject)

    def release(self):
        self.cap.release()


@dataclasses.dataclass
class Caption:
    text: str
    x: float
    y: float
    size: int = 150
    write_rate: float = 0.02
    wait_s: float = 1.0

    def show(self, scene: Scene, scale: float, pos: Tuple[float, float], grid_size: float) -> None:
        texts = self.text.split(" | ")
        kwargs = dict(font="FreeSans", font_size=self.size)
        if len(texts) > 0:
            text = Paragraph(*texts, **kwargs)
        else:
            text = Text(texts[0], **kwargs)
        text.scale(scale).move_to([pos[0] + self.x * grid_size, pos[1] + self.y * grid_size, 0])
        if self.write_rate > 0:
            run_time = self.write_rate * len(self.text)
            scene.play(Write(text, run_time=run_time))
            scene.wait(self.wait_s)
            scene.play(Unwrite(text, run_time=run_time))
        else:
            scene.add(text)
            scene.wait(self.wait_s)
            scene.remove(text)


class Video(Scene):
    captions = {
        2: [
            Caption("JFK International Airport", 0, -1.5),
            Caption(
                "Airbus A320 airliner modified to burn | hydrogen fuel, starting at 27200-L capacity",
                0, -0.75
            ),
        ],
        32: [Caption("Takeoff", 0, -0.75)],
        470: [
            Caption("AT200 cargo UAV from | Pittsburgh International Airport", -2, 0.75),
            Caption("Airliner slows down to match UAV's speed", 1.5, -0.5),
        ],
        553: [Caption("UAV docks with airliner for mid-air refueling", 0, 0.5)],
        880: [
            Caption("UAV lands at Pittsburgh | International Airport", 1, -1),
            Caption("A second UAV takes off for further refueling", -1, -1.25),
        ],
        1227: [Caption("The second UAV returns to | Pittsburgh International Airport", 1.5, 0.75)],
        1280: [Caption("The airliner returns to cruise speed", 0, 0.5)],
        1330: [Caption("JFK", 2, 0.25), Caption("PIT", 0.75, 0.25)],
        1511: [Caption("Another UAV, from Denver | International Airport", -1.75, 0.5)],
        1760: [Caption("A second UAV from DEN", 0, -0.5)],
        1830: [Caption("A third UAV", 0, -0.5)],
        1900: [Caption("A fourth", 0, -0.5)],
        2230: [
            Caption("The UAVs land at DEN", 1, -1.25),
            Caption("Another three UAVs taking | off in succession", -1.5, -1.25),
        ],
        2555: [Caption("The airliner is now en route to LAX", 0, 0.5)],
        2755: [Caption("LAX International | Airport", -2.5, -1.5)],
        2995: [Caption("The airliner has completed its | 4000-km, hydrogen-powered flight | from JFK to LAX after 7h", 0, -1.25)],
    }

    def _make_grid(self, xs, ys):
        h_lines = Group(*[Line(start=np.array([xs[0], y, 0]), end=np.array([xs[-1], y, 0])) for y in ys])
        v_lines = Group(*[Line(start=np.array([x, ys[0], 0]), end=np.array([x, ys[-1], 0])) for x in xs])
        grid_size = xs[1] - xs[0]
        return Group(*[h_lines, v_lines]), grid_size

    def construct(self):
        viz_w, viz_h = 1800, 900
        graph_w, graph_h = 640, 426
        denom = (viz_h * graph_w + 2 * graph_h * viz_w)

        # viz_scale = W / viz_w * (2 / 3)
        viz_wp = (2 * W * graph_h * viz_w) / denom
        viz_scale = viz_wp / viz_w
        viz_pos = (
            np.array([-(W - viz_w * viz_scale), H - viz_h * viz_scale])
            / 2
            / PX_PER_UNIT
        )
        viz = VideoFeed(
            fpath="electric_airliner_video-Airliner-side-view.avi",
            scale=viz_scale,
            pos=viz_pos,
        )
        # graph_scale = W / graph_w * (1 / 3)
        graph_wp = (W * viz_h * graph_w) / denom
        graph_scale = graph_wp / graph_w
        soc_graph = VideoFeed(
            fpath="electric_airliner_video-Airliner-soc-graph.avi",
            scale=graph_scale,
            pos=(
                np.array([W - graph_w * graph_scale, H - graph_h * graph_scale])
                / 2
                / PX_PER_UNIT
            ),
        )
        speed_graph = VideoFeed(
            fpath="electric_airliner_video-Airliner-speed-graph.avi",
            scale=graph_scale,
            pos=(
                np.array([W - graph_w * graph_scale, H - graph_h * graph_scale * 3])
                / 2
                / PX_PER_UNIT
            ),
        )
        video_feeds = [viz, soc_graph, speed_graph]

        self.frame_i_15fps = 0

        grid, _ = self._make_grid(
            xs=np.arange(-8, 8), ys=np.arange(-5, 5)
        )
        viz_grid, viz_grid_size = self._make_grid(
            xs=(
                np.linspace(-viz_w, viz_w, 8 + 1) / 2 / PX_PER_UNIT * viz_scale
                + viz_pos[0]
            ),
            ys=(
                np.linspace(-viz_h, viz_h, 4 + 1) / 2 / PX_PER_UNIT * viz_scale
                + viz_pos[1]
            ),
        )
        grids = Group()

        while True:
            if self.frame_i_15fps > N_15FPS_FRAMES:
                break
            for video_feed in video_feeds:
                video_feed.add_to(scene=self)
            self.add(grids)
            frame_captions = self.captions.get(self.frame_i_15fps)
            if frame_captions is not None:
                for caption in frame_captions:
                    caption.show(scene=self, scale=viz_scale, pos=viz_pos, grid_size=viz_grid_size)
            else:
                self.wait(1 / FRAME_RATE)
                # Caption(
                #     f"{self.frame_i}", y=1, write_rate=0, wait_s=(1 / FRAME_RATE)
                # ).show(scene=self)
            self.remove(grids)
            for video_feed in video_feeds:
                video_feed.remove_from(scene=self)
            self.frame_i_15fps += 1

        for video_feed in video_feeds:
            video_feed.release()
