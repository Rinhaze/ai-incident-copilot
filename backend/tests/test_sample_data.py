from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import sample_data


def test_demo_seed_is_reproducible_and_idempotent(tmp_path, monkeypatch):
    target = create_engine(f"sqlite:///{tmp_path / 'demo.db'}")
    monkeypatch.setattr(sample_data, "engine", target)
    monkeypatch.setattr(sample_data, "SessionLocal", sessionmaker(bind=target, expire_on_commit=False))
    first = sample_data.seed_demo(42)
    second = sample_data.seed_demo(42)
    assert first == {"accepted": 3, "duplicates": 0, "incidents": 1}
    assert second == {"accepted": 0, "duplicates": 3, "incidents": 1}
