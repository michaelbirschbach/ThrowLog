from pathlib import Path

from throwlog.config import load_config
from throwlog.paths import ensure_session
from throwlog.pipeline import next_unimplemented, stage_names


def test_stage_order_starts_at_ingest():
    assert stage_names()[0] == "ingest"
    assert stage_names()[-1] == "confidence"
    assert "export" not in stage_names()


def test_first_stage_is_unimplemented():
    assert next_unimplemented(Path("."), load_config()) == "ingest"


def test_session_folder_is_created(tmp_path, monkeypatch):
    import throwlog.paths as paths

    monkeypatch.setattr(paths, "SESSIONS", tmp_path)
    created = ensure_session("img_0138")
    assert (created / "export").is_dir()
    assert (created / "throws").is_dir()
