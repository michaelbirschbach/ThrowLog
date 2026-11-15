# ThrowLog

ThrowLog turns practice video into a per-throw workload log for the Red Sox Baseball Innovation Challenge. This repository is the scaffold: the package layout, the output schema, the configuration file, and the stage order. Detection is not implemented yet.

## What is here

- `config/default.yaml` holds every threshold. Stage code reads that file.
- `throwlog/schemas.py` is the per-throw record and the session summary.
- `throwlog/export.py` writes CSV and JSON only after a record passes the schema.
- `throwlog/pipeline.py` lists the stages. The first call stops at `ingest`, which is not built yet.
- `data/raw/` is gitignored. Local video stays on this machine.
- `data/manifests/` is tracked and describes those clips without storing the pixels.

## Local clip

`data/raw/img_0138.mov` is a slow-motion bullpen throw, one pitcher, copied from a phone video on November 15, 2026.

| | |
| --- | --- |
| Playback | 20.2 seconds, 30 fps |
| Display | 720 by 1280, portrait |
| Stored frames | 1280 by 720, H.264, with a rotation ingest must apply |
| Timing | Playback time of the slow-motion export. Not confirmed as real time. |

This clip is for wiring up ingest and pose. The application proof of concept still needs a separate public clip of two players playing catch, with a hand count of the throws. Do not commit either video.

## Setup

Python 3.11 is the runtime for the vision stack. This Mac currently has the system Python 3.9.6, and Python 3.11 is not installed. The scaffold itself runs on 3.9.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
throwlog check
pytest
```

Install the detector only after Python 3.11 is available:

```bash
pip install -e ".[dev,vision]"
```

The pose model is Ultralytics, which is AGPL-3.0. This repository is AGPL-3.0 for that reason. If the challenge rules require the code to stay private, swap the detector before publishing. See the project plan.

The proof of concept is meant to run on this MacBook Pro (M1 Pro, 16 GB) through Metal (`device: mps` in the config). Long club videos, after selection, run on a rented NVIDIA GPU.

## Commands

```bash
throwlog stages    # stage order and which one is next
throwlog check     # load config and print the local clip
throwlog session img_0138
```

`python app/streamlit_app.py`, `python tools/label_tool.py`, and `python eval/run_eval.py` exit with a short explanation. Those tools are scheduled for after selection.

## Stage order

ingest, track, pose, throws, ball, pairing, identity, geometry, velocity, confidence, then export.

Build them in that order. A stage writes files under `data/sessions/<id>/` and can be rerun on its own. Do not score a session that was used to train a model or to set a threshold.
