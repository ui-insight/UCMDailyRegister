"""Employee News rename and staff-only employee announcements (#441)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


ROOT = Path(__file__).parents[1]
MIGRATION_PATH = ROOT / "alembic" / "versions" / "f1b3d5e7a9c2_employee_news_categories.py"
SEED_PATH = ROOT / "data" / "allowed_values" / "allowed_values.json"


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("employee_news", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded_categories() -> dict[str, dict]:
    return {
        value["Code"]: value
        for value in json.loads(SEED_PATH.read_text())
        if value["Value_Group"] == "Submission_Category"
    }


def test_migration_matches_seed():
    seeds = seeded_categories()
    for code, values in load_migration().CATEGORY_UPDATES.items():
        for key, value in values.items():
            assert seeds[code][key] == value, (code, key)


def test_migration_updates_only_the_two_categories_and_is_idempotent():
    migration = load_migration()
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData()
    table = sa.Table(
        "allowed_values",
        metadata,
        sa.Column("Id", sa.Integer, primary_key=True),
        sa.Column("Value_Group", sa.String(100)),
        sa.Column("Code", sa.String(100)),
        sa.Column("Label", sa.String(255)),
        sa.Column("Description", sa.Text),
        sa.Column("Display_Order", sa.Integer),
        sa.Column("Visibility_Role", sa.String(50)),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(table.insert(), [
            {"Value_Group": "Submission_Category", "Code": "employee_announcement",
             "Label": "Employee (Faculty/Staff)", "Description": "Old", "Display_Order": 0,
             "Visibility_Role": "public"},
            {"Value_Group": "Submission_Category", "Code": "faculty_staff",
             "Label": "Faculty/Staff", "Description": "Old", "Display_Order": 1,
             "Visibility_Role": "public"},
            {"Value_Group": "Submission_Category", "Code": "kudos",
             "Label": "Kudos", "Description": "Keep", "Display_Order": 4,
             "Visibility_Role": "public"},
        ])
        for _ in range(2):
            migration.apply_category_updates(connection)
        rows = {row["Code"]: row for row in connection.execute(sa.select(table)).mappings()}

    assert rows["faculty_staff"]["Label"] == "Employee News (Faculty/Staff)"
    assert rows["faculty_staff"]["Display_Order"] == 0
    assert rows["employee_announcement"]["Visibility_Role"] == "staff"
    assert rows["kudos"]["Label"] == "Kudos"
    assert rows["kudos"]["Description"] == "Keep"
