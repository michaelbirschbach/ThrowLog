# ThrowLog

ThrowLog reads a practice video and writes a per-throw workload log for the Red Sox Baseball Innovation Challenge. A finished throw record carries a time, the thrower, the receiver or a wall drill, the ball type, the distance in feet, and a velocity in miles per hour with a range. Low-confidence throws are flagged for a person to review.

## What works today

`throwlog run` takes a session from the video through a paired throw:

1. **Ingest** decodes the phone video, applies the display rotation, and records the frame rate.
2. **Track and pose** use one Ultralytics pose model to find the people, estimate body keypoints, and keep a track id with ByteTrack.
3. **Throws** mark wrist-speed peaks as candidates.
4. **Identity** joins split track ids that belong to the same person.
5. **Ball** confirms a candidate when a ball is in flight.
6. **Pairing** calls the throw a catch when another person is on screen, and names that person as the receiver. A thrower alone in the frame is a wall drill.

Distance, velocity, and the confidence score are the remaining stages. The export writer already checks every row against that contract and refuses a row that does not match. It does not yet receive a distance or a velocity from the pipeline.

Every threshold lives in `config/default.yaml`. The stage code reads that file.

## Current check

On a local two-person catch clip, a hand count of the near thrower found six releases. The ball detector placed a ball in flight within about half a second of each of them. Four of the six also lined up with a wrist-speed candidate, and each of those was paired as a catch to the other player. The other two releases were seen as ball flights only. A few extra wrist peaks remain. One of them, a keypoint jump with no ball leaving the hand, was left unpaired.

The ball label on that clip is `white`. A second ball color has not been filmed. The map from color to the club's ball name is empty until that mapping is provided.

The clip used for this check is not in the repository. Timestamps on the slow-motion bullpen clip below are playback time, not real time, and are not miles per hour.

## Repository layout

- `throwlog/` is the pipeline.
- `config/default.yaml` holds the thresholds.
- `throwlog/schemas.py` defines the per-throw record and the session summary.
- `data/manifests/` describes local clips without storing the video.
- `data/raw/` and `data/sessions/` stay on the machine that runs the analysis.

## Run it

Python 3.9 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,vision]"
pytest
throwlog stages
```

`throwlog run <session_id>` reads the video named in `data/manifests/<session_id>.yaml` and writes the session under `data/sessions/<session_id>/`. The video file itself is not in git.

The proof of concept runs on Apple Silicon through Metal (`device: mps` in the config). Longer club video, after selection, is planned for an NVIDIA GPU.

The review app, the labeling tool, and the held-out evaluation are stubs. They are scheduled for after selection.

## Development clips

`data/manifests/img_0138.yaml` describes a slow-motion bullpen throw, one pitcher, filmed on a phone.

| | |
| --- | --- |
| Playback | 20.2 seconds, 30 fps |
| Display | 720 by 1280, portrait |
| Stored frames | 1280 by 720, H.264. Ingest applies the rotation. |
| Timing | Playback time of the slow-motion export. |

A separate two-person catch clip was used only as a local check of tracking, the ball, and pairing. It is third-party footage. It is not in the repository, and it is not the public example.

## Third-party model

Person detection, pose, and tracking use Ultralytics YOLO11n-pose and ByteTrack. Ultralytics is licensed under the GNU AGPL-3.0. This repository is AGPL-3.0 for that reason.

## Stage order

`throwlog run` executes ingest, track, pose, throws, identity, ball, and pairing. Identity runs before the ball stage so a person who was split across track ids is counted once.

Geometry, velocity, and confidence follow. A session used to set a threshold is not later used as the score for that same choice.
