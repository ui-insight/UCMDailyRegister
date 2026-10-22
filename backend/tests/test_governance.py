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
