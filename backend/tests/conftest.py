import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_session
from app.main import app

@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    def override():
        session = factory()
        try: yield session
        finally: session.close()
    app.dependency_overrides[get_session] = override
    with TestClient(app) as test_client: yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
