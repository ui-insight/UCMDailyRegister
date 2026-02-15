"""Shared pytest fixtures for UCM Newsletter Builder tests."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.api.deps import get_db
from app.main import app as fastapi_app
import app.models  # noqa: F401 — register all models


# In-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for all tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async DB session for direct model access in tests."""
    async with TestSession() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient wired to the FastAPI app with test DB."""

    async def override_get_db():
        async with TestSession() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


# --- Factory helpers ---


def make_submission_data(**overrides) -> dict:
    """Return a valid SubmissionCreate dict with sensible defaults."""
    data = {
        "Category": "faculty_staff",
        "Target_Newsletter": "tdr",
        "Original_Headline": "Test Submission Headline",
        "Original_Body": "This is the body text of a test submission.",
        "Submitter_Name": "Test User",
        "Submitter_Email": "test@uidaho.edu",
    }
    data.update(overrides)
    return data


def make_style_rule_data(**overrides) -> dict:
    """Return a valid StyleRuleCreate dict with sensible defaults."""
    data = {
        "Rule_Set": "shared",
        "Category": "grammar",
        "Rule_Key": "test_rule",
        "Rule_Text": "This is a test rule.",
        "Severity": "warning",
    }
    data.update(overrides)
    return data


def make_newsletter_data(**overrides) -> dict:
    """Return a valid NewsletterCreate dict with sensible defaults."""
    data = {
        "Newsletter_Type": "tdr",
        "Publish_Date": "2026-03-01",
    }
    data.update(overrides)
    return data
