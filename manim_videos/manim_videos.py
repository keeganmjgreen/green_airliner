import dataclasses
from typing import Optional, Tuple

import cv2
from manim import *
from manim.mobject.text import text_mobject

from src.utils.utils import _getenv


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
        for l in lines + ["last line"]:
            if l.strip() != "":
                if l.startswith(TITLE):
                    title = l.removeprefix(TITLE).strip()
                    self._title(title)
                elif l.startswith(HEADER):
                    self._slide(slide_title, "\n".join(slide_bullets))
                    slide_bullets = []
                    slide_title = l.removeprefix(HEADER).strip()
                elif l.startswith(INDENT):
                    slide_bullets.append(l.removeprefix(INDENT).strip())

    def construct(self):
        raise NotImplementedError


class Intro(BaseSlideshowVideo):
    def construct(self):
        self.add(ImageMobject("splash-blurred-dimmed.png"))
        self._slides_from_file(f"{_getenv('REPO_DIR')}/manim_videos/intro.md")


class Conclusion(BaseSlideshowVideo):
    def construct(self):
        self.add(ImageMobject("splash-blurred-dimmed.png"))
        self._slides_from_file(f"{_getenv('REPO_DIR')}/manim_videos/conclusion.md")


# ==================================================================================================
# Video

text_mobject.TEXT_MOB_SCALE_FACTOR = 0.01
text_mobject.DEFAULT_LINE_SPACING_SCALE = 0.8

config.max_files_cached = 4000

PX_PER_UNIT = 135


@dataclasses.dataclass
class VideoFeed:
    name: str
    fpath_lineup: List[str]
    scale: float
    pos: np.array
    crop_to_width: Optional[float] = None

    def __post_init__(self):
        self.caps = [cv2.VideoCapture(fpath) for fpath in self.fpath_lineup]

    def add_to(self, scene: Scene):
        for cap in self.caps:
            not_done, frame = cap.read()
            if not_done:
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
    n_frames = 3000
    frame_rate = 15
    w = 1920
    h = 1080
    indices = False
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
        1700: [Caption("Another UAV, from Denver | International Airport", -1.75, 0.5)],
        1800: [Caption("A second UAV from DEN", 0, -0.5)],
        1900: [Caption("A third UAV", 0, -0.5)],
        2230: [
            Caption("The UAVs land at DEN", 1, -1.25),
            Caption("Another two UAVs taking | off in succession", -1.5, -1.25),
        ],
        2555: [Caption("The airliner is now en route to LAX", 0, 0.5)],
        2755: [Caption("LAX International | Airport", -2.5, -1.5)],
        3000: [Caption("The airliner has completed its | 4000-km, hydrogen-powered flight | from JFK to LAX after 7h", 0, -1.25)],
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
        )
        # graph_scale = W / graph_w * (1 / 3)
        graph_wp = (self.w * viz_h * graph_w) / denom
        graph_scale = graph_wp / graph_w
        graph_hp = graph_h * graph_scale
        soc_graph = VideoFeed(
            name="Airliner SoC graph",
            fpath_lineup=["inputs/Airliner-soc-graph.avi"],
            scale=graph_scale,
            pos=(np.array([self.w - graph_wp, self.h - graph_hp]) / 2),
        )
        speed_graph = VideoFeed(
            name="Airliner speed graph",
            fpath_lineup=["inputs/Airliner-speed-graph.avi"],
            scale=graph_scale,
            pos=(np.array([self.w - graph_wp, self.h - graph_hp * 3]) / 2),
        )
        map_scale = (self.h - viz_h * viz_scale) / viz_h
        map_wp = viz_w * map_scale
        map_hp = viz_h * map_scale
        map_view = VideoFeed(
            name="Map view",
            fpath_lineup=["inputs/-map-view.avi"],
            scale=map_scale,
            pos=(np.array([-(self.w - map_wp), -(self.h - map_hp)]) / 2),
        )
        uav_crop_to_width = (self.w - map_wp) / 2 / map_scale
        uav1_view = VideoFeed(
            name="PIT/DEN-UAV-0 side view",
            fpath_lineup=[
                "inputs/-UAV-0-side-view.avi",
                "inputs/DEN-UAV-0-side-view.avi",
            ],
            scale=map_scale,
            pos=np.array(
                [
                    -self.w / 2 + map_wp + uav_crop_to_width * map_scale / 2,
                    -(self.h - map_hp) / 2,
                ]
            ),
            crop_to_width=uav_crop_to_width,
        )
        uav2_view = VideoFeed(
            name="PIT/DEN-UAV-1 side view",
            fpath_lineup=[
                "inputs/PIT-UAV-1-side-view.avi",
                "inputs/DEN-UAV-1-side-view.avi",
            ],
            scale=map_scale,
            pos=np.array(
                [
                    -self.w / 2 + map_wp + uav_crop_to_width * map_scale * 3 / 2,
                    -(self.h - map_hp) / 2,
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
            vline(x=(self.w / 2 - graph_wp), y1=(self.h / 2), y2=(self.h / 2 - viz_hp)),
            # Line between graphs:
            hline(x1=(self.w / 2 - graph_wp), x2=(self.w / 2), y=(self.h / 2 - graph_hp)),
            # Line between airliner view and map view & UAV view(s):
            hline(x1=(-self.w / 2), x2=(self.w / 2), y=(self.h / 2 - viz_hp)),
            # Line between map view and first UAV view:
            vline(x=(-self.w / 2 + map_wp), y1=(self.h / 2 - viz_hp), y2=(-self.h / 2)),
            # Line between first and second UAV views:
            vline(
                x=(-self.w / 2 + map_wp + uav_crop_to_width * map_scale),
                y1=(self.h / 2 - viz_hp),
                y2=(-self.h / 2),
            ),
        )

        while True:
            if self.frame_i > self.n_frames:
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
                if not self.indices:
                    self.wait(1 / self.frame_rate)
                else:
                    Caption(
                        f"{self.frame_i}", x=0, y=0, write_rate=0, wait_s=(1 / self.frame_rate)
                    ).show(scene=self, scale=viz_scale, pos=viz_pos, grid_size=viz_grid_size)
            self.remove(lines)
            self.remove(grids)
            for video_feed in video_feeds:
                video_feed.remove_from(scene=self)
            self.frame_i += 1

        for video_feed in video_feeds:
            video_feed.release()
