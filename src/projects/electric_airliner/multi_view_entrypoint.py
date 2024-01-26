from subprocess import Popen

track_airplane_id = "Airliner"

Popen(
    [
        "python",
        "src/projects/electric_airliner/study_runner.py",
        "--view", "airplane-side-view",
        "--n-view-columns", "2",
        "--track-airplane-id", track_airplane_id,
    ]
)
Popen(
    [
        "python",
        "src/projects/electric_airliner/study_runner.py",
        "--view", "airplane-tail-view",
        "--n-view-columns", "2",
        "--track-airplane-id", track_airplane_id,
    ]
)
