import dataclasses
import os
from typing import Optional, Tuple

import numpy as np

import cv2
from manim import *
from manim.mobject.text import text_mobject


# ==================================================================================================
# Intro and Conclusion

class BaseSlideshowVideo(Scene):
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
        if title_str is not None:
            title = Title(f"{self.tex_style} {title_str}")
            self.play(Write(title), run_time=title_write_time)
            self.wait(pause_time)
        bullets = [f"{self.tex_style} {b.strip()}" for b in bullets_str.split("\n") if b.strip() != ""]
        blist = BulletedList(*bullets, width=250)
        self.play(Write(blist), run_time=bullets_write_time)
        self.wait(wait_time)
        self.play(Unwrite(blist), run_time=bullets_unwrite_time)
        if title_str is not None:
            self.play(Unwrite(title), run_time=title_unwrite_time)

    def _slides_from_file(self, fpath: str):
        with open(fpath) as f:
            lines = f.readlines()
        TITLE = "# "
        HEADER = "## "
        INDENT = "- "
        slide_title = None
        slide_bullets = []
        for l in lines + ["## last line"]:
            if l.strip() != "":
                if l.startswith(TITLE):
                    title = l.removeprefix(TITLE).strip()
                    self._title(title)
                elif l.startswith(HEADER):
                    if slide_bullets != []:
                        self._slide(slide_title, "\n".join(slide_bullets))
                        slide_bullets = []
                    slide_title = l.removeprefix(HEADER).strip()
                elif l.startswith(INDENT):
                    slide_bullets.append(l.removeprefix(INDENT).strip())

    def construct(self):
        raise NotImplementedError


class Intro(BaseSlideshowVideo):
    def construct(self):
        self.add(ImageMobject("splash-blurred150-dimmed50.png"))
        self._slides_from_file(f"{os.environ['REPO_DIR']}/manim_videos/intro.md")


class Conclusion(BaseSlideshowVideo):
    def construct(self):
        self.add(ImageMobject("splash-blurred150-dimmed50.png"))
        self._slides_from_file(f"{os.environ['REPO_DIR']}/manim_videos/conclusion.md")


# ==================================================================================================
# Video

text_mobject.TEXT_MOB_SCALE_FACTOR = 0.01
text_mobject.DEFAULT_LINE_SPACING_SCALE = 0.8

config.max_files_cached = 4000

PX_PER_UNIT = 135


@dataclasses.dataclass
class Caption:
    text: str
    x: float
    y: float
    size: int = 125
    scale: bool = False
    color: ManimColor = dataclasses.field(default_factory=(lambda: WHITE))
    write_rate: float = 0.02
    wait_s: float = 1.0

    def show(self, scene: Scene, scale: float, pos: Tuple[float, float], grid_size_px: float) -> None:
        texts = self.text.split(" | ")
        kwargs = dict(font="FreeSans", font_size=self.size, color=self.color)
        if len(texts) > 0:
            text = Paragraph(*texts, **kwargs)
        else:
            text = Text(texts[0], **kwargs)
        if self.scale:
            text.scale(scale)
        text.move_to((pos[0] / PX_PER_UNIT + self.x * grid_size_px / PX_PER_UNIT, pos[1] / PX_PER_UNIT + self.y * grid_size_px / PX_PER_UNIT, 0))
        if self.write_rate > 0:
            run_time = self.write_rate * len(self.text)
            scene.play(Write(text, run_time=run_time))
            scene.wait(self.wait_s)
            scene.play(Unwrite(text, run_time=run_time))
        else:
            scene.add(text)
            scene.wait(self.wait_s)
            scene.remove(text)


@dataclasses.dataclass
class VideoFeed:
    name: str
    fpath_lineup: List[str]
    scale: float
    pos: np.array
    scaled_size: Tuple[float, float]
    grids_per_h: float = 4
    show_grid: bool = False
    crop_to_width: Optional[float] = None
    captions: Dict[float, List[Caption]] = dataclasses.field(default_factory=dict)
    show_indices: bool = False

    def __post_init__(self):
        self.caps = [cv2.VideoCapture(fpath) for fpath in self.fpath_lineup]

        w, h = self.scaled_size
        self.grid_size_px = h / self.grids_per_h
        half_xs = np.arange(0, w / 2 + 1e-3, self.grid_size_px)
        half_ys = np.arange(0, h / 2 + 1e-3, self.grid_size_px)
        self.grid = self._make_grid(
            xs=(
                self.pos[0] + np.concatenate([-half_xs[::-1], half_xs])
            ) / PX_PER_UNIT,
            ys=(
                self.pos[1] + np.concatenate([-half_ys[::-1], half_ys])
            ) / PX_PER_UNIT,
        )

    def _make_grid(self, xs, ys, stroke_width: float = 0.5, color: ManimColor = BLACK) -> Group:
        h_lines = Group(*[Line(start=np.array([xs[0], y, 0]), end=np.array([xs[-1], y, 0]), stroke_width=stroke_width, color=color) for y in ys])
        v_lines = Group(*[Line(start=np.array([x, ys[0], 0]), end=np.array([x, ys[-1], 0]), stroke_width=stroke_width, color=color) for x in xs])
        return Group(*[h_lines, v_lines])

    def add_to(self, scene: Scene):
        for cap in self.caps:
            not_done, frame = cap.read()
            if not_done:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if self.crop_to_width is not None:
                    h, w, _ = frame.shape
                    frame = frame[
                        :,
                        int((w - self.crop_to_width / self.scale) // 2) : w
                        - int((w - self.crop_to_width / self.scale) // 2),
                    ]
                self.image_mobject = (
                    ImageMobject(frame)
                    .scale(self.scale)
                    .move_to([*(self.pos / PX_PER_UNIT), 0])
                )
                break
        scene.add(self.image_mobject)

        if self.show_grid:
            scene.add(self.grid)

        self.captions_to_show = self.captions.get(scene.frame_i, [])

    def remove_from(self, scene: Scene):
        if self.show_grid:
            scene.remove(self.grid)

        scene.remove(self.image_mobject)

    def release(self):
        for cap in self.caps:
            cap.release()


class Video(Scene):
    n_frames = 2820
    frame_rate = 30
    w = 1920
    h = 1080
    show_grid: bool = False

    def construct(self):
        viz_w, viz_h = 1800, 900
        graph_w, graph_h = 640, 445 # 426
        denom = (viz_h * graph_w + 2 * graph_h * viz_w)

        # viz_scale = W / viz_w * (2 / 3)
        viz_wp = (2 * self.w * graph_h * viz_w) / denom
        viz_scale = viz_wp / viz_w
        viz_hp = viz_h * viz_scale
        viz_pos = (
            np.array([-(self.w - viz_w * viz_scale), self.h - viz_h * viz_scale])
            / 2
            / PX_PER_UNIT
        )
        viz = VideoFeed(
            name="Airliner side view",
            fpath_lineup=["inputs/Airliner-side-view.avi"],
            scale=viz_scale,
            pos=(viz_pos * PX_PER_UNIT),
            scaled_size=(viz_wp, viz_hp),
            show_grid=self.show_grid,
            captions={
                3: [
                    Caption("JFK International Airport", 0, -1.5, color=BLACK),
                    Caption(
                        "Airbus A320 airliner modified to burn | hydrogen fuel, starting at 27200-L capacity",
                        0, -0.75, color=BLACK
                    ),
                ],
                35: [Caption("Takeoff", 0, -0.75)],
                410: [
                    Caption("AT200 cargo UAV from | Pittsburgh International Airport", -1.5, 0.75),
                    Caption("Airliner slows down to match UAV’s speed", 1, -0.5),
                ],
                505: [Caption("UAV docks with airliner for mid-air refueling", 0, 0.5)],
                890: [
                    Caption("UAV lands at Pittsburgh | International Airport", 0.5, -1.5),
                    Caption("A second UAV takes off for further refueling", -1, -1.25),
                ],
                1180: [Caption("The second UAV returns to | Pittsburgh International Airport", 2, 1.25)],
                1220: [Caption("The airliner returns to cruise speed", 0, 0.5)],
                1207: [Caption("PIT", 2.5, -0.75)],
                1470: [Caption("Another UAV, from Denver | International Airport", -1.5, 0.5)],
                1755: [Caption("A second UAV from DEN", 0, -0.5)],
                1895: [Caption("A third UAV", 0, -0.5)],
                2172: [
                    Caption("The UAVs land at DEN", 0.5, -1.25),
                    Caption("Another two UAVs taking | off in succession", -1.5, -1.25),
                ],
                2325: [Caption("The airliner is now en route to LAX", 0, 0.5)],
                2590: [Caption("LAX International | Airport", -1.75, -1.25)],
                2780: [Caption(
                    "The airliner has completed its | 4000-km, hydrogen-powered flight | from JFK to LAX after 7h", 0,
                    -1, color=BLACK)],
            },
            # show_indices=True,
        )
        # graph_scale = W / graph_w * (1 / 3)
        graph_wp = (self.w * viz_h * graph_w) / denom
        graph_scale = graph_wp / graph_w
        graph_hp = graph_h * graph_scale
        energy_level_graph = VideoFeed(
            name="Airliner energy level graph",
            fpath_lineup=["inputs/Airliner-energy-level-graph.avi"],
            scale=graph_scale,
            pos=(np.array([self.w - graph_wp, self.h - graph_hp]) / 2),
            scaled_size=(graph_wp, graph_hp),
            show_grid=self.show_grid,
            captions={
                3: [Caption("Graphs of airliner’s | energy level | and speed over time", 0, -1.6, color=BLACK)],
            },
        )
        speed_graph = VideoFeed(
            name="Airliner speed graph",
            fpath_lineup=["inputs/Airliner-speed-graph.avi"],
            scale=graph_scale,
            pos=(np.array([self.w - graph_wp, self.h - graph_hp * 3]) / 2),
            scaled_size=(graph_wp, graph_hp),
            show_grid=self.show_grid,
        )
        map_scale = (self.h - viz_h * viz_scale) / viz_h
        map_wp = viz_w * map_scale
        map_hp = viz_h * map_scale
        map_view = VideoFeed(
            name="Map view",
            fpath_lineup=["inputs/-map-view.avi"],
            scale=map_scale,
            pos=(np.array([-(self.w - map_wp), -(self.h - map_hp)]) / 2),
            scaled_size=(map_wp, map_hp),
            show_grid=self.show_grid,
        )
        uav_crop_to_width = (self.w - map_wp) / 2
        uav1_view = VideoFeed(
            name="PIT/DEN_UAV_0 side view",
            fpath_lineup=[
                "inputs/PIT_UAV_0-side-view.avi",
                "inputs/DEN_UAV_0-side-view.avi",
            ],
            scale=map_scale,
            pos=np.array(
                [
                    -self.w / 2 + map_wp + uav_crop_to_width / 2,
                    -(self.h - map_hp) / 2,
                ]
            ),
            scaled_size=(uav_crop_to_width, map_hp),
            show_grid=self.show_grid,
            crop_to_width=uav_crop_to_width,
            captions={
                3: [
                    Caption(
                        "2 refueling UAVs ready at | Pittsburgh International Airport",
                        3,
                        1.25,
                        color=BLACK,
                    )
                ],
            },
        )
        uav2_view = VideoFeed(
            name="PIT/DEN_UAV_1 side view",
            fpath_lineup=[
                "inputs/PIT_UAV_1-side-view.avi",
                "inputs/DEN_UAV_1-side-view.avi",
            ],
            scale=map_scale,
            pos=np.array(
                [
                    -self.w / 2 + map_wp + uav_crop_to_width * 3 / 2,
                    -(self.h - map_hp) / 2,
                ]
            ),
            scaled_size=(uav_crop_to_width, map_hp),
            show_grid=self.show_grid,
            crop_to_width=uav_crop_to_width,
        )
        video_feeds = [viz, energy_level_graph, speed_graph, map_view, uav1_view, uav2_view]

        self.frame_i = 0

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
            vline(x=(self.w / 2 - graph_wp), y1=(self.h / 2), y2=(self.h / 2 - viz_hp)),
            # Line between graphs:
            hline(x1=(self.w / 2 - graph_wp), x2=(self.w / 2), y=(self.h / 2 - graph_hp)),
            # Line between airliner view and map view & UAV view(s):
            hline(x1=(-self.w / 2), x2=(self.w / 2), y=(self.h / 2 - viz_hp)),
            # Line between map view and first UAV view:
            vline(x=(-self.w / 2 + map_wp), y1=(self.h / 2 - viz_hp), y2=(-self.h / 2)),
            # Line between first and second UAV views:
            vline(
                x=(-self.w / 2 + map_wp + uav_crop_to_width),
                y1=(self.h / 2 - viz_hp),
                y2=(-self.h / 2),
            ),
        )

        while True:
            if self.frame_i > self.n_frames:
                break
            for video_feed in video_feeds:
                video_feed.add_to(scene=self)
            self.add(lines)
            for vf in video_feeds:
                if not vf.show_indices:
                    for caption in vf.captions_to_show:
                        caption.show(scene=self, scale=vf.scale, pos=vf.pos, grid_size_px=vf.grid_size_px)
                else:
                    Caption(
                        f"{self.frame_i}", x=0, y=0, write_rate=0, wait_s=(1 / self.frame_rate)
                    ).show(scene=self, scale=vf.scale, pos=vf.pos, grid_size_px=vf.grid_size_px)
                    break
            self.wait(1 / self.frame_rate)
            self.remove(lines)
            for video_feed in video_feeds:
                video_feed.remove_from(scene=self)
            self.frame_i += 1

        for video_feed in video_feeds:
            video_feed.release()
