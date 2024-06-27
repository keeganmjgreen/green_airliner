"""
Intro:
    conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -ql /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Intro && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/Intro.mp4
    conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qm /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Intro && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/Intro.mp4
    conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qH /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Intro && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/Intro.mp4

Video:
    conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -ql /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/Video.mp4
    conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qm /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/Video.mp4
    conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qH /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/Video.mp4

Combine:
    conda activate electric_airline && cd /home/keegan_green/Dropbox/Documents/Projects/electric_airline/ && python combine_manim_videos.py --work-dir=/home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/ && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/final.mp4
    conda activate electric_airline && cd /home/keegan_green/Dropbox/Documents/Projects/electric_airline/ && python combine_manim_videos.py --work-dir=/home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/ && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/final.mp4
    conda activate electric_airline && cd /home/keegan_green/Dropbox/Documents/Projects/electric_airline/ && python combine_manim_videos.py --work-dir=/home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/ && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/final.mp4
"""

import dataclasses
from typing import Optional, Tuple

import cv2
from manim import *

from manim.mobject.text import text_mobject


# ==================================================================================================
# Intro

class Intro(Scene):
    tex_style = r"\sf"

    def _title(
        self,
        title_str: str,
        tex_size: str = "huge",
        width: float = 200,
        write_time: float = 1.0,
        wait_time: float = 3.0,
        unwrite_time: float = 0.5,
    ) -> None:
        title = Tex(f"{self.tex_style} \{tex_size} {title_str}", width=width)
        self.play(Write(title), run_time=write_time)
        self.wait(wait_time)
        self.play(Unwrite(title), run_time=unwrite_time)

    def _slide(
        self,
        title_str: str,
        bullets_str: str,
        title_write_time: float = 1.0,
        pause_time: float = 1.0,
        bullets_write_time: float = 2.0,
        wait_time: float = 15.0,
        bullets_unwrite_time: float = 1.0,
        title_unwrite_time: float = 0.5,
    ) -> None:
        title = Title(f"{self.tex_style} {title_str}")
        self.play(Write(title), run_time=title_write_time)
        self.wait(pause_time)
        bullets = [f"{self.tex_style} {b.strip()}" for b in bullets_str.split("\n") if b.strip() != ""]
        blist = BulletedList(*bullets, width=250)
        self.play(Write(blist), run_time=bullets_write_time)
        self.wait(wait_time)
        self.play(Unwrite(blist), run_time=bullets_unwrite_time)
        self.play(Unwrite(title), run_time=title_unwrite_time)

    def construct(self):
        self._title("Simulation of Mid-Air Refueling of a Hydrogen-Powered Commercial Airliner")
        self._slide(
            "The Problem",
            """
            Commercial airliners contribute massive amounts of CO2 emissions, which is incompatible with the current goal of attaining net zero by 2050 to help mitigate the climate crisis.
            Airliners and passengers are refusing to reduce air travel and will continue to do so until oil reserves are depleted (in which case the damage is done), unless a similarly affordable alternative is created.
            Unless batteries or green fuel technology improves dramatically (which is unlikely), electric commercial airliners of similar size and serving similar routes will be infeasible.
            """
        )
        self._slide(
            "Proposed Solution",
            """
            Use of green alternatives to jet fuel is limited by their comparatively low energy density; storing the same amount of energy requires carrying far more weight, requiring more fuel, and so on.
            Mid-air refueling of commercial airliners by jet-fueled UAVs (which would travel shorter distances) may be a solution.
            The extra weight in green fuel would be efficiently carried and delivered to the airliner by UAVs operating out of airports over which the airliner flies.
            Each UAV would take off, dock with the airliner to partially refuel it, then land again for its own refueling.
            """
        )


# ==================================================================================================
# Video

text_mobject.TEXT_MOB_SCALE_FACTOR = 0.01
text_mobject.DEFAULT_LINE_SPACING_SCALE = 0.8

config.max_files_cached = 4000

N_FRAMES = 1500
FRAME_RATE = 15
W = 1920
H = 1080
PX_PER_UNIT = 135


class VideoCapture(cv2.VideoCapture):
    not_done: bool = True


@dataclasses.dataclass
class VideoFeed:
    name: str
    fpath_lineup: List[str]
    scale: float
    pos: np.array
    crop_to_width: Optional[float] = None

    def __post_init__(self):
        self.caps = [VideoCapture(fpath) for fpath in self.fpath_lineup]

    def add_to(self, scene: Scene):
        for cap in self.caps:
            if cap.not_done:
                cap.not_done, frame = cap.read()
                if cap.not_done:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    if self.crop_to_width is not None:
                        h, w, _ = frame.shape
                        frame = frame[
                            :,
                            int((w - self.crop_to_width) // 2) : w
                            - int((w - self.crop_to_width) // 2),
                        ]
                    self.image_mobject = (
                        ImageMobject(frame)
                        .scale(self.scale)
                        .move_to([*(self.pos / PX_PER_UNIT), 0])
                    )
                    break
        scene.add(self.image_mobject)

    def remove_from(self, scene: Scene):
        scene.remove(self.image_mobject)

    def release(self):
        for cap in self.caps:
            cap.release()


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
            Caption("Airliner slows down to match UAV’s speed", 1.5, -0.5),
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
        viz_hp = viz_h * viz_scale
        viz_pos = (
            np.array([-(W - viz_w * viz_scale), H - viz_h * viz_scale])
            / 2
            / PX_PER_UNIT
        )
        viz = VideoFeed(
            name="Airliner side view",
            fpath_lineup=["electric_airliner_video-Airliner-side-view.avi"],
            scale=viz_scale,
            pos=(viz_pos * PX_PER_UNIT),
        )
        # graph_scale = W / graph_w * (1 / 3)
        graph_wp = (W * viz_h * graph_w) / denom
        graph_scale = graph_wp / graph_w
        graph_hp = graph_h * graph_scale
        soc_graph = VideoFeed(
            name="Airliner SoC graph",
            fpath_lineup=["electric_airliner_video-Airliner-soc-graph.avi"],
            scale=graph_scale,
            pos=(np.array([W - graph_wp, H - graph_hp]) / 2),
        )
        speed_graph = VideoFeed(
            name="Airliner speed graph",
            fpath_lineup=["electric_airliner_video-Airliner-speed-graph.avi"],
            scale=graph_scale,
            pos=(np.array([W - graph_wp, H - graph_hp * 3]) / 2),
        )
        map_scale = (H - viz_h * viz_scale) / viz_h
        map_wp = viz_w * map_scale
        map_hp = viz_h * map_scale
        map_view = VideoFeed(
            name="Map view",
            fpath_lineup=["electric_airliner_video--map-view.avi"],
            scale=map_scale,
            pos=(np.array([-(W - map_wp), -(H - map_hp)]) / 2),
        )
        uav_crop_to_width = (W - map_wp) / 2 / map_scale
        uav1_view = VideoFeed(
            name="PIT/DEN-UAV-0 side view",
            fpath_lineup=[
                "electric_airliner_video-PIT-UAV-0-side-view.avi",
                "electric_airliner_video-DEN-UAV-0-side-view.avi",
            ],
            scale=map_scale,
            pos=np.array(
                [
                    -W / 2 + map_wp + uav_crop_to_width * map_scale / 2,
                    -(H - map_hp) / 2,
                ]
            ),
            crop_to_width=uav_crop_to_width,
        )
        uav2_view = VideoFeed(
            name="PIT/DEN-UAV-1 side view",
            fpath_lineup=[
                "electric_airliner_video-PIT-UAV-1-side-view.avi",
                "electric_airliner_video-DEN-UAV-1-side-view.avi",
            ],
            scale=map_scale,
            pos=np.array(
                [
                    -W / 2 + map_wp + uav_crop_to_width * map_scale * 3 / 2,
                    -(H - map_hp) / 2,
                ]
            ),
            crop_to_width=uav_crop_to_width,
        )
        video_feeds = [viz, soc_graph, speed_graph, map_view, uav1_view, uav2_view]

        self.frame_i = 0

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

        def line(start: Tuple[float, float], end: Tuple[float, float]):
            return Line(
                start=(np.array([*start, 0]) / PX_PER_UNIT),
                end=(np.array([*end, 0]) / PX_PER_UNIT),
                color=BLACK,
            )

        def hline(x1: float, x2: float, y: float):
            return line(start=(x1, y), end=(x2, y))

        def vline(x: float, y1: float, y2: float):
            return line(start=(x, y1), end=(x, y2))

        lines = Group(
            # Line between airliner view and graphs:
            vline(x=(W / 2 - graph_wp), y1=(H / 2), y2=(H / 2 - viz_hp)),
            # Line between graphs:
            hline(x1=(W / 2 - graph_wp), x2=(W / 2), y=(H / 2 - graph_hp)),
            # Line between airliner view and map view & UAV view(s):
            hline(x1=(-W / 2), x2=(W / 2), y=(H / 2 - viz_hp)),
            # Line between map view and first UAV view:
            vline(x=(-W / 2 + map_wp), y1=(H / 2 - viz_hp), y2=(-H / 2)),
            # Line between first and second UAV views:
            vline(
                x=(-W / 2 + map_wp + uav_crop_to_width * map_scale),
                y1=(H / 2 - viz_hp),
                y2=(-H / 2),
            ),
        )

        while True:
            if self.frame_i > N_FRAMES:
                break
            for video_feed in video_feeds:
                video_feed.add_to(scene=self)
            self.add(grids)
            self.add(lines)
            frame_captions = self.captions.get(self.frame_i)
            if frame_captions is not None:
                for caption in frame_captions:
                    caption.show(scene=self, scale=viz_scale, pos=viz_pos, grid_size=viz_grid_size)
            else:
                self.wait(1 / FRAME_RATE)
                # Caption(
                #     f"{self.frame_i}", x=0, y=0, write_rate=0, wait_s=(1 / FRAME_RATE)
                # ).show(scene=self, scale=viz_scale, pos=viz_pos, grid_size=viz_grid_size)
            self.remove(lines)
            self.remove(grids)
            for video_feed in video_feeds:
                video_feed.remove_from(scene=self)
            self.frame_i += 1

        for video_feed in video_feeds:
            video_feed.release()
