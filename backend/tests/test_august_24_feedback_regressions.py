"""Deployment-equivalent coverage for the Aug. 24 UCM feedback reports."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import sqlalchemy as sa


BACKEND_PATH = Path(__file__).parents[1]
RULES_PATH = BACKEND_PATH / "data" / "style_rules" / "shared_rules.json"
ALLOWED_VALUES_PATH = BACKEND_PATH / "data" / "allowed_values" / "allowed_values.json"
MIGRATION_PATH = (
    BACKEND_PATH / "alembic" / "versions" / "d8a2f4b6c9e1_address_august_24_feedback.py"
)


def load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("august_24_feedback", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seeded_rules() -> dict[str, dict]:
    return {rule["rule_key"]: rule for rule in json.loads(RULES_PATH.read_text())}


def test_seed_preserves_intended_headline_action_and_complete_event_sentences():
    rules = seeded_rules()

    headline_rule = rules["headline_reader_perspective"]
    assert "attend a reading, not read or purchase the book" in headline_rule["rule_text"]
    assert headline_rule["severity"] == "error"

    ordering_rule = rules["event_detail_ordering"]
    assert "same complete sentence as the event name" in ordering_rule["rule_text"]
    assert "Never begin a separate sentence with a time" in ordering_rule["rule_text"]

    sentence_rule = rules["short_sentences"]
    assert "Never separate an event from its time, date or location" in sentence_rule["rule_text"]


def test_employee_announcement_seed_appears_first_with_requested_label():
    categories = [
        value
        for value in json.loads(ALLOWED_VALUES_PATH.read_text())
        if value["Value_Group"] == "Submission_Category"
    ]
    first = min(categories, key=lambda category: category["Display_Order"])

    assert first["Code"] == "employee_announcement"
    assert first["Label"] == "Employee (Faculty/Staff)"


def test_feedback_migration_is_idempotent_and_matches_managed_seed_data():
    migration = load_migration()
    metadata = sa.MetaData()
    style_rules = sa.Table(
        "style_rules",
        metadata,
        sa.Column("Id", sa.String(36), primary_key=True),
        sa.Column("Rule_Set", sa.String(50), nullable=False),
        sa.Column("Category", sa.String(100), nullable=False),
        sa.Column("Rule_Key", sa.String(100), nullable=False),
        sa.Column("Rule_Text", sa.Text, nullable=False),
        sa.Column("Is_Active", sa.Boolean, nullable=False),
        sa.Column("Severity", sa.String(50), nullable=False),
    )
    allowed_values = sa.Table(
        "allowed_values",
        metadata,
        sa.Column("Id", sa.String(36), primary_key=True),
        sa.Column("Value_Group", sa.String(100), nullable=False),
        sa.Column("Code", sa.String(100), nullable=False),
        sa.Column("Label", sa.String(255), nullable=False),
        sa.Column("Display_Order", sa.Integer, nullable=False),
    )
    engine = sa.create_engine("sqlite://")
    metadata.create_all(engine)

    with engine.begin() as connection:
        connection.execute(
            style_rules.insert().values(
                Id="headline-rule",
                Rule_Set="shared",
                Category="headlines",
                Rule_Key="headline_reader_perspective",
                Rule_Text="Old text",
                Is_Active=False,
                Severity="warning",
            )
        )
        connection.execute(
            allowed_values.insert(),
            [
                {
                    "Id": "employee",
                    "Value_Group": "Submission_Category",
                    "Code": "employee_announcement",
                    "Label": "Employee Announcement",
                    "Display_Order": 6,
                },
                {
                    "Id": "student",
                    "Value_Group": "Submission_Category",
                    "Code": "student",
                    "Label": "Student",
                    "Display_Order": 2,
                },
            ],
        )

        migration._apply_august_24_feedback_updates(connection)
        migration._apply_august_24_feedback_updates(connection)

        rule_rows = connection.execute(sa.select(style_rules)).mappings().all()
        employee = (
            connection.execute(
                sa.select(allowed_values).where(allowed_values.c.Code == "employee_announcement")
            )
            .mappings()
            .one()
        )
        student = (
            connection.execute(sa.select(allowed_values).where(allowed_values.c.Code == "student"))
            .mappings()
            .one()
        )

    seeds = seeded_rules()
    assert len(rule_rows) == len(migration.STYLE_RULE_UPDATES)
    for row in rule_rows:
        seed = seeds[row["Rule_Key"]]
        assert row["Rule_Text"] == seed["rule_text"]
        assert row["Category"] == seed["category"]
        assert row["Severity"] == seed["severity"]
        assert row["Is_Active"] is True

    assert employee["Label"] == "Employee (Faculty/Staff)"
    assert employee["Display_Order"] == 0
    assert student["Label"] == "Student"
    assert student["Display_Order"] == 2
