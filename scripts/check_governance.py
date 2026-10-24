#!/usr/bin/env python3
"""Validate governance contracts and render catalog/reference pages without a DB.

Run with --write to refresh generated Markdown after a reviewed catalog/seed
change. The default is read-only and fails on drift, incomplete metadata,
invalid/ambiguous evidence, missing source files or overdue assertion review.
"""

import argparse
import ast
import json
from collections import Counter
from datetime import date
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "frontend/src/data/governance-catalog.json"
CATEGORIES = {
    "submission_source", "publication_archive", "external_working", "feedback", "configuration",
}


def model_columns():
    tables = {}
    for path in sorted((ROOT / "backend/app/models").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if not isinstance(node, ast.ClassDef):
                continue
            table, columns = None, []
            for member in node.body:
                if isinstance(member, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "__tablename__"
                    for target in member.targets
                ):
                    table = ast.literal_eval(member.value)
                if (isinstance(member, ast.AnnAssign)
                        and isinstance(member.value, ast.Call)
                        and isinstance(member.value.func, ast.Name)
                        and member.value.func.id == "mapped_column"):
                    columns.append(member.target.id)
            if table:
                tables[table] = columns
    return tables


def unique(values, label):
    duplicates = [key for key, count in Counter(values).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate {label}: {duplicates}")


def validate_evidence(data, schema, as_of):
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    unique([item["id"] for item in data["requirements"]], "requirement IDs")
    unique([item["status"] for item in data["status_values"]], "status definitions")
    for item in data["requirements"]:
        assertion = item["current_assertion"]
        if assertion["status"] != "not_started":
            if not assertion["validated_at"] or not assertion["validated_by"]:
                raise ValueError(f"Missing assertion review: {item['id']}")
            age = (as_of - date.fromisoformat(assertion["validated_at"])).days
            if age < 0 or age > 180:
                raise ValueError(f"Assertion review date is future or over 180 days old: {item['id']}")
        for source in item["evidence_sources"]:
            if source["type"] in {"repo_file", "repo_directory"}:
                path = (ROOT / source["path"]).resolve()
                if not path.is_relative_to(ROOT):
                    raise ValueError("Evidence path must remain in repository")
                valid = path.is_file() if source["type"] == "repo_file" else path.is_dir()
                if not valid:
                    raise ValueError(f"Missing or wrong-kind source: {source['path']}")


def validate_catalog(catalog, models, groups):
    unique([table["name"] for table in catalog["tables"]], "catalog tables")
    actual = {table["name"]: [column["name"] for column in table["columns"]]
              for table in catalog["tables"]}
    if actual != {name: fields for name, fields in sorted(models.items())}:
        raise ValueError("Catalog table/column names or order differ from ORM; review metadata")
    if not catalog.get("reviewedAt") or not catalog.get("reviewStatus"):
        raise ValueError("Catalog needs review metadata")
    date.fromisoformat(catalog["reviewedAt"])
    for table in catalog["tables"]:
        for key in ["description", "steward", "sourceSystem", "area", "status"]:
            if not table.get(key):
                raise ValueError(f"Missing {key}: {table['name']}")
        if table["status"] not in {"Communications extension", "Operational support", "UDM-derived pattern"}:
            raise ValueError("Unknown extension status")
        if table.get("retentionCategory") not in CATEGORIES:
            raise ValueError("Unknown retention category")
        unique([column["name"] for column in table["columns"]], "catalog columns")
        for column in table["columns"]:
            if not column.get("description") or type(column.get("pii")) is not bool:
                raise ValueError(f"Incomplete column: {table['name']}.{column['name']}")
            if column.get("classification") not in {"Public", "Internal", "Confidential", "Restricted"}:
                raise ValueError("Unknown data classification")
            if column.get("allowedValueGroup") and column["allowedValueGroup"] not in groups:
                raise ValueError(f"Missing seed group: {column['allowedValueGroup']}")


def render_dictionary(catalog):
    lines = ["# Data dictionary", "",
             "Generated from `frontend/src/data/governance-catalog.json`; used by the staff governance page.",
             "Update reviewed metadata in that file, then run `python scripts/check_governance.py --write`.",
             "", f"Catalog review: {catalog['reviewedAt']}; **{catalog['reviewStatus']}**.", "",
             "Labels describe default handling, not institutional classification approval. PII flags include",
             "incidental personal information risk; published release decisions apply to individual content.",
             "Retention categories are defined in [Retention and disposal](retention.md).", ""]
    for table in catalog["tables"]:
        lines += [f"## `{table['name']}`", "", table["description"], "",
                  f"Steward role: {table['steward']}. Source: {table['sourceSystem']}.",
                  f"Retention category: `{table['retentionCategory']}`. Extension: {table['status']}.", "",
                  "| Column | Meaning | Handling | PII risk | Vocabulary |",
                  "| --- | --- | --- | --- | --- |"]
        for column in table["columns"]:
            description = column['description'].replace('|', '\\|')
            lines.append(f"| `{column['name']}` | {description} | {column['classification']} | "
                         f"{'Yes' if column['pii'] else 'No'} | {column.get('allowedValueGroup', '—')} |")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_reference(seed, models):
    groups = sorted({row["Value_Group"] for row in seed})
    def seed_count(folder):
        return sum(len(json.loads(path.read_text()))
                   for path in (ROOT / "backend/data" / folder).glob("*.json"))
    lines = ["# Bootstrap reference inventory", "", "Generated by `scripts/check_governance.py` from model declarations and seed JSON.",
             "Seeds are a bootstrap baseline; live database values may differ. Existing staff edits survive",
             "normal seeding; deliberate overwrite requires `SEED_OVERWRITE=1`.", "",
             "| Inventory | Count |", "| --- | ---: |",
             f"| ORM tables | {len(models)} |", f"| Mapped columns | {sum(map(len, models.values()))} |",
             f"| Newsletter sections | {seed_count('sections')} |",
             f"| Style rules | {seed_count('style_rules')} |",
             f"| Schedule configurations | {len(json.loads((ROOT / 'backend/data/schedule/schedule_config.json').read_text()))} |",
             f"| AllowedValue groups | {len(groups)} |", f"| AllowedValue values | {len(seed)} |", "",
             "| Value group | Codes |", "| --- | --- |"]
    for group in groups:
        codes = ", ".join(f"`{row['Code']}`" for row in seed if row["Value_Group"] == group)
        lines.append(f"| `{group}` | {codes} |")
    lines += ["", "## Code-governed exceptions", "",
              "Some discriminators are still code-validated: SLC category/routing (`slc_event`, `none`)",
              "are used by staff/import paths but absent from bootstrap allowed values; event classification",
              "(`strategic`, `signature`), recurrence, override actions, auth roles, feedback states, AI task",
              "states (`queued`, `running`, `succeeded`, `failed`) and AI",
              "provider identifiers also have code-level contracts. Do not claim all enums are DB-backed.",
              "These need explicit schema/API/seed review before adding new values. Runtime additions",
              "must be reconciled through a reviewed seed/catalog change; no automatic production sync exists.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    catalog = json.loads(CATALOG_PATH.read_text())
    models = model_columns()
    seed = json.loads((ROOT / "backend/data/allowed_values/allowed_values.json").read_text())
    unique([(row['Value_Group'], row['Code']) for row in seed], "seed codes")
    validate_catalog(catalog, models, {row['Value_Group'] for row in seed})
    evidence_dir = ROOT / "docs/governance/enterprise-ai-framework"
    validate_evidence(json.loads((evidence_dir / 'evidence.json').read_text()),
                      json.loads((evidence_dir / 'evidence.schema.json').read_text()), args.as_of)
    for name, content in {"data-dictionary.md": render_dictionary(catalog),
                          "reference-data.md": render_reference(seed, models)}.items():
        path = ROOT / "docs/governance" / name
        if args.write:
            path.write_text(content)
        elif not path.exists() or path.read_text() != content:
            raise ValueError(f"Generated documentation drift: {path.relative_to(ROOT)}; use --write")
    print(f"Governance valid: {len(models)} tables, {sum(map(len, models.values()))} columns")


if __name__ == "__main__":
    main()
