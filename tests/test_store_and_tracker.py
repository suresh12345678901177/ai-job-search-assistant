import importlib

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    from jobseeker import config

    data_dir = tmp_path / "data"
    monkeypatch.setattr(config, "DATA_DIR", data_dir)
    monkeypatch.setattr(config, "JOBS_DIR", data_dir / "jobs")
    monkeypatch.setattr(config, "GENERATED_DIR", data_dir / "generated")
    monkeypatch.setattr(config, "SESSIONS_DIR", data_dir / "sessions")
    monkeypatch.setattr(config, "PROFILE_PATH", data_dir / "profile.json")
    monkeypatch.setattr(config, "QA_BANK_PATH", data_dir / "qa_bank.json")
    monkeypatch.setattr(config, "TRACKER_DB_PATH", data_dir / "tracker.db")

    from jobseeker import store, tracker

    importlib.reload(store)
    importlib.reload(tracker)
    return store, tracker


def test_save_and_load_job(isolated_data_dir):
    store, _ = isolated_data_dir
    job_id = store.save_job({"title": "Backend Engineer", "company": "Acme", "url": "http://x", "description": "..."})
    loaded = store.load_job(job_id)
    assert loaded["title"] == "Backend Engineer"
    assert loaded["id"] == job_id
    assert loaded in store.list_jobs()


def test_qa_bank_round_trip(isolated_data_dir):
    store, _ = isolated_data_dir
    store.add_qa_entry("Why this role?", "Because X", "job-1", "Engineer", "Acme")
    bank = store.load_qa_bank()
    assert len(bank) == 1
    assert bank[0]["question"] == "Why this role?"


def test_profile_save_and_load(isolated_data_dir):
    store, _ = isolated_data_dir
    store.save_profile({"summary": "hi"})
    assert store.load_profile()["summary"] == "hi"


def test_tracker_upsert_and_status(isolated_data_dir):
    _, tracker = isolated_data_dir
    tracker.upsert("job-1", "Backend Engineer", "Acme", "http://x")
    tracker.set_status("job-1", "applied")
    rows = tracker.list_all()
    assert rows[0]["status"] == "applied"


def test_tracker_rejects_unknown_status(isolated_data_dir):
    _, tracker = isolated_data_dir
    tracker.upsert("job-1", "Backend Engineer", "Acme", "http://x")
    with pytest.raises(ValueError):
        tracker.set_status("job-1", "not-a-real-status")
