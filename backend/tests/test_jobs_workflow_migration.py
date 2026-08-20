"""Deployment-equivalent coverage for the completed Jobs workflow."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "b5d7f9a1c3e4_finalize_jobs_workflow.py"
)
SECTIONS_PATH = Path(__file__).parents[1] / "data" / "sections" / "tdr_sections.json"


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("finalize_jobs_workflow", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_jobs_section_order_migration_is_idempotent_and_matches_seed():
    migration = load_migration()
    metadata = sa.MetaData()
    sections = sa.Table(
        "newsletter_sections",
        metadata,
        sa.Column("Id", sa.String(36), primary_key=True),
        sa.Column("Newsletter_Type", sa.String(50), nullable=False),
        sa.Column("Name", sa.String(255), nullable=False),
        sa.Column("Slug", sa.String(255), nullable=False),
        sa.Column("Display_Order", sa.Integer, nullable=False),
        sa.Column("Description", sa.Text),
        sa.Column("Requires_Image", sa.Boolean, nullable=False),
        sa.Column("Is_Active", sa.Boolean, nullable=False),
    )
    engine = sa.create_engine("sqlite://")
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            sections.insert().values(
                Id="jobs",
                Newsletter_Type="tdr",
                Name="Job Opportunities",
                Slug="job-opportunities",
                Display_Order=8,
                Description="Old description",
                Requires_Image=False,
                Is_Active=True,
            )
        )
        migration._apply_jobs_section_update(connection)
        migration._apply_jobs_section_update(connection)
        row = connection.execute(sa.select(sections)).mappings().one()

    seeded = next(
        section
        for section in json.loads(SECTIONS_PATH.read_text())
        if section["slug"] == "job-opportunities"
    )
    assert row["Display_Order"] == seeded["display_order"]
    assert row["Description"] == seeded["description"]
