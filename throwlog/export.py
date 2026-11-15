"""Write schema-valid throw records. Invalid rows are refused before any file is written."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from throwlog.schemas import PlayerSessionSummary, ThrowRecord

THROW_FIELDS = list(ThrowRecord.model_fields)


def dumps_throws(throws: list[ThrowRecord]) -> list[dict]:
    checked = [ThrowRecord.model_validate(row.model_dump()) for row in throws]
    return [row.model_dump(mode="json") for row in checked]


def write_throws_json(throws: list[ThrowRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dumps_throws(throws), indent=2) + "\n")


def write_throws_csv(throws: list[ThrowRecord], path: Path) -> None:
    rows = dumps_throws(throws)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=THROW_FIELDS)
        writer.writeheader()
        for row in rows:
            row["component_conf"] = json.dumps(row["component_conf"], sort_keys=True)
            writer.writerow(row)


def write_summary_json(summaries: list[PlayerSessionSummary], path: Path) -> None:
    checked = [PlayerSessionSummary.model_validate(row.model_dump()) for row in summaries]
    payload = [row.model_dump(mode="json") for row in checked]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")
