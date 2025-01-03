from argparse import ArgumentParser
from pathlib import Path

from moviepy.editor import VideoFileClip, concatenate_videoclips

parser = ArgumentParser()
parser.add_argument("--work-dir")
args = parser.parse_args()

clips = [
    VideoFileClip(str(Path(args.work_dir, f"Video.mp4"))).subclip("00:00:39", "00:00:41"),
    VideoFileClip(str(Path(args.work_dir, f"Intro.mp4"))),
    VideoFileClip(str(Path(args.work_dir, f"Video.mp4"))),
]
final = concatenate_videoclips(clips)
final.write_videofile(str(Path(args.work_dir, "video_presentation.mp4")))
final.write_gif(str(Path(args.work_dir, "video_presentation.gif")))
