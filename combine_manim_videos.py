from argparse import ArgumentParser
from pathlib import Path

from moviepy.editor import VideoFileClip, concatenate_videoclips

FNAMES = ["Intro", "Video"]

parser = ArgumentParser()
parser.add_argument("--work-dir")
args = parser.parse_args()

clips = [VideoFileClip(str(Path(args.work_dir, f"{fname}.mp4"))) for fname in FNAMES]
final = concatenate_videoclips(clips)
final.write_videofile(str(Path(args.work_dir, "final.mp4")))
