"""Focused tests for deterministic AI system-prompt contracts."""

from app.services.ai.prompts import build_system_prompt


def test_system_prompt_requires_a_final_rule_compliance_audit():
    prompt = build_system_prompt(
        newsletter_type="tdr",
        category="faculty_staff",
        style_rules=[
            {
                "category": "formatting",
                "rule_key": "spell_out_acronyms",
                "rule_text": "Define every acronym on first reference.",
                "severity": "error",
            }
        ],
    )

    assert "Before returning JSON, audit the draft against every [MUST] rule" in prompt
    assert "Revise the draft until every [MUST] rule is satisfied" in prompt


def test_static_prompt_does_not_override_the_jobs_style_rule():
    prompt = build_system_prompt(
        newsletter_type="tdr",
        category="job_opportunity",
        style_rules=[
            {
                "category": "formatting",
                "rule_key": "job_posting_format",
                "rule_text": "Use a single linked line with title, unit and non-Moscow location.",
                "severity": "error",
            }
        ],
    )

    assert "For job postings: use only the title and link" not in prompt
    assert "For Jobs-category submissions, the active Jobs style rule takes precedence" in prompt


def test_prompt_allows_only_rule_approved_canonical_enrichment():
    prompt = build_system_prompt(
        newsletter_type="myui",
        category="student",
        style_rules=[],
    )

    assert "except canonical expansions or addresses explicitly approved by an active rule" in prompt
