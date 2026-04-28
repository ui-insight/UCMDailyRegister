"""Tests for production schema management boundaries."""

import inspect

from app import main
from app.db import seed


def test_app_startup_does_not_create_database_schema():
    """Production startup must not mutate schema outside Alembic migrations."""
    source = inspect.getsource(main.lifespan)

    assert "create_all" not in source


def test_seed_all_does_not_create_database_schema():
    """Reference seeding assumes an already migrated database."""
    source = inspect.getsource(seed.seed_all)

    assert "create_all" not in source
