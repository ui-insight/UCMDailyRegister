"""Every deterministic post-edit check reports a rule that exists."""

import inspect
import json
import re
from pathlib import Path

from app.services.ai import post_checks

SEED_DIR = Path(__file__).parents[1] / "data" / "style_rules"


def test_every_check_names_a_seeded_rule():
    seeded = {
        rule["rule_key"]
        for path in SEED_DIR.glob("*_rules.json")
        for rule in json.loads(path.read_text(encoding="utf-8"))
    }
    source = inspect.getsource(post_checks)
    named = set(re.findall(r'(?:Finding|_each|_listed)\(\s*"([a-z_]+)"', source))
    assert named, "no rule keys found; the pattern above needs updating"
    assert named <= seeded, sorted(named - seeded)


def test_source_checks_are_skipped_without_a_source():
    context = post_checks.CheckContext(
        headline="Register now",
        body="Contact Jordan Example at jexample@example.edu.",
        category="faculty_staff",
    )
    checks = post_checks.OUTPUT_CHECKS + post_checks.SOURCE_CHECKS
    assert len(set(checks)) == len(checks)
    assert not any(
        finding.rule_key == "no_fabricated_content"
        for finding in post_checks.run_checks(context)
    )
