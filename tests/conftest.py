import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker 
from testcontainers.postgres import PostgresContainer
from fastapi.testclient import TestClient
from models.job import Base
from app.main import app
from db.database import get_db

@pytest.fixture(scope="function")
def db_session_factory(postgres_container):
    """Farklı worker'ları simüle etmek için taze session üreten fabrika."""
    engine = create_engine(postgres_container)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="function")
def db_session(postgres_container):
    db_engine = create_engine(postgres_container)
    Base.metadata.create_all(bind=db_engine)
    SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=db_engine)

@pytest.fixture(scope="function")
def client(db_session):
    def ovveride_get_db():
        yield db_session
    app.dependency_overrides[get_db] = ovveride_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
