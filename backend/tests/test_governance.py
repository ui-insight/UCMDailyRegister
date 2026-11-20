"""Governance coverage and schema rejection tests; no live data is accessed."""

import copy
import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("governance_check", ROOT / "scripts/check_governance.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


def manifest():
    folder = ROOT / "docs/governance/enterprise-ai-framework"
    return (json.loads((folder / "evidence.json").read_text()),
            json.loads((folder / "evidence.schema.json").read_text()))


def test_catalog_covers_actual_sqlalchemy_metadata():
    from app.db.base import Base
    import app.models  # noqa: F401

    catalog = json.loads(checks.CATALOG_PATH.read_text())
    actual = {table['name']: {column['name'] for column in table['columns']}
              for table in catalog['tables']}
    assert actual == {name: {column.name for column in table.columns}
                      for name, table in Base.metadata.tables.items()}


@pytest.mark.parametrize("mutation", ["missing_path", "bad_url", "duplicate_id", "overdue_review"])
def test_evidence_rejects_ambiguous_or_invalid_sources(mutation):
    data, schema = manifest()
    data = copy.deepcopy(data)
    if mutation == "missing_path":
        data['requirements'][0]['evidence_sources'][0] = {'type': 'repo_file', 'label': 'No path'}
    elif mutation == "bad_url":
        data['requirements'][0]['evidence_sources'][0] = {
            'type': 'external_url', 'label': 'Invalid URL', 'url': 'not a URL',
        }
    elif mutation == "duplicate_id":
        data['requirements'].append(copy.deepcopy(data['requirements'][0]))
    else:
        data['requirements'][0]['current_assertion']['validated_at'] = '2025-01-01'
    with pytest.raises((ValueError, ValidationError)):
        checks.validate_evidence(data, schema, date(2026, 10, 22))


def test_catalog_rejects_new_undocumented_model_column():
    catalog = json.loads(checks.CATALOG_PATH.read_text())
    models = checks.model_columns()
    models['submissions'].append('Unreviewed_Field')
    with pytest.raises(ValueError, match='differ from ORM'):
        checks.validate_catalog(catalog, models, set())


def seed_groups():
    seed = json.loads((ROOT / "backend/data/allowed_values/allowed_values.json").read_text())
    return {row['Value_Group'] for row in seed}


def test_catalog_accepts_current_apm_tiers():
    catalog = json.loads(checks.CATALOG_PATH.read_text())
    checks.validate_catalog(catalog, checks.model_columns(), seed_groups())


@pytest.mark.parametrize("mutation, message", [
    ("missing_column_tier", "Missing or unknown APM 30.11 tier"),
    ("unknown_column_tier", "Missing or unknown APM 30.11 tier"),
    ("table_below_columns", "highest column tier"),
    ("table_above_columns", "highest column tier"),
    ("not_proposed", "apm3011 status 'proposed'"),
])
def test_catalog_rejects_invalid_apm_tiers(mutation, message):
    catalog = json.loads(checks.CATALOG_PATH.read_text())
    tables = {table['name']: table for table in catalog['tables']}
    if mutation == "missing_column_tier":
        del tables['submissions']['columns'][0]['apm3011Tier']
    elif mutation == "unknown_column_tier":
        tables['submissions']['columns'][0]['apm3011Tier'] = 'Confidential'
    elif mutation == "table_below_columns":
        tables['submissions']['apm3011Tier'] = 'Low'
    elif mutation == "table_above_columns":
        tables['allowed_values']['apm3011Tier'] = 'Moderate'
    else:
        catalog['apm3011']['status'] = 'approved'
    with pytest.raises(ValueError, match=message):
        checks.validate_catalog(catalog, checks.model_columns(), seed_groups())
