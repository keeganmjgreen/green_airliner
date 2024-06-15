"""
conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -ql /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/480p15/Video.mp4
conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qm /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/720p30/Video.mp4
conda activate electric_airline && cd /home/keegan_green/Downloads/electric_airliner_video/ && manim -qH /home/keegan_green/Dropbox/Documents/Projects/electric_airline/manim_video.py Video && vlc /home/keegan_green/Downloads/electric_airliner_video/media/videos/manim_video/1080p60/Video.mp4
"""

import dataclasses

import cv2
from manim import *

from manim.mobject.text import text_mobject

text_mobject.TEXT_MOB_SCALE_FACTOR = 0.01
text_mobject.DEFAULT_LINE_SPACING_SCALE = 0.8

config.max_files_cached = 4000

N_15FPS_FRAMES = 3000
FRAME_RATE = 15


@dataclasses.dataclass
class Caption:
    text: str
    x: float = 0.0
    y: float = 0.0
    size: int = 150
    write_rate: float = 0.02
    wait_s: float = 1.0

    def show(self, scene: Scene) -> None:
        texts = self.text.split(" | ")
        kwargs = dict(font="FreeSans", font_size=self.size)
        if len(texts) > 0:
            text = Paragraph(*texts, **kwargs)
        else:
            text = Text(texts[0], **kwargs)
        text.to_edge(UP).shift([self.x, -self.y, 0])
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
            Caption("JFK International Airport", y=5.5),
            Caption(
                "Airbus A320 airliner modified to burn | hydrogen fuel, starting at 27200-L capacity",
                y=4.5,
            ),
        ],
        32: [Caption("Takeoff", y=5)],
        470: [
            Caption("AT200 cargo UAV from | Pittsburgh International Airport", x=-2.5, y=2),
            Caption("Airliner slows down to match UAV's speed", x=2.5, y=4),
        ],
        553: [Caption("UAV docks with airliner for mid-air refueling", y=2.5)],
        880: [
            Caption("UAV lands at Pittsburgh | International Airport", x=1.5, y=5),
            Caption("A second UAV takes off for further refueling", x=-2, y=5.5),
        ],
        1227: [Caption("The second UAV returns to | Pittsburgh International Airport", x=1.5, y=2)],
        1280: [Caption("The airliner returns to cruise speed", y=2.5)],
        1330: [Caption("JFK", x=3.5, y=3), Caption("PIT", x=1.25, y=3)],
        1511: [Caption("Another UAV, from Denver | International Airport", x=-3, y=2.25)],
        1760: [Caption("A second UAV from DEN", y=4)],
        1830: [Caption("A third UAV", y=4)],
        1900: [Caption("A fourth", y=4)],
        2230: [
            Caption("The UAVs land at DEN", x=1.5, y=5.5),
            Caption("Another three UAVs taking | off in succession", x=-2, y=5),
        ],
        2555: [Caption("The airliner is now en route to LAX", y=2.5)],
        2755: [Caption("LAX International | Airport", x=-4, y=5.5)],
        2995: [Caption("The airliner has completed its 4000-km, hydrogen- | powered flight from JFK to LAX after 7h", y=5.5, size=100)],
    }

    def construct(self):
        cap = cv2.VideoCapture("electric_airliner_video.avi")

        self.frame_i_15fps = 0

        while True:
            flag, frame = cap.read()
            if not flag or N_15FPS_FRAMES is not None and self.frame_i_15fps > N_15FPS_FRAMES:
                break
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_img = ImageMobject(frame)
            self.add(frame_img)
            frame_captions = self.captions.get(self.frame_i_15fps)
            if frame_captions is not None:
                for caption in frame_captions:
                    caption.show(scene=self)
            else:
                self.wait(1 / FRAME_RATE)
                # Caption(
                #     f"{self.frame_i}", y=1, write_rate=0, wait_s=(1 / FRAME_RATE)
                # ).show(scene=self)
            self.remove(frame_img)
            self.frame_i_15fps += 1

        cap.release()
