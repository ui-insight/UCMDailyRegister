"""Focused tests for deterministic AI system-prompt contracts."""

from app.services.ai.prompts import build_compliance_repair_prompt, build_system_prompt


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


def test_prompt_authorizes_flagged_acronym_expansions():
    prompt = build_system_prompt(
        newsletter_type="tdr",
        category="faculty_staff",
        style_rules=[],
    )

    assert "an acronym's full name when the acronym rule requires a first-reference definition" in prompt
    assert "flag any full name you supply" in prompt


def test_length_section_has_no_stray_blank_line_for_non_jobs_categories():
    prompt = build_system_prompt(
        newsletter_type="tdr",
        category="faculty_staff",
        style_rules=[],
    )

    assert "excessive detail.\n- Collapse bullet lists" in prompt


def test_jobs_guidance_line_is_embedded_cleanly_for_jobs_submissions():
    prompt = build_system_prompt(
        newsletter_type="tdr",
        category="job_opportunity",
        style_rules=[],
    )

    assert "precedence over generic length and structure guidance.\n- Collapse bullet lists" in prompt


def test_compliance_repair_prompt_includes_draft_and_deterministic_findings():
    prompt = build_compliance_repair_prompt(
        "Original editing request",
        "Attend Tumbbad",
        "Watch Tumbbad at the Kenworthy.",
        [
            {
                "rule_key": "composition_title_format",
                "message": "Composition title needs AP quotation formatting: 'Tumbbad'",
            }
        ],
    )

    assert "Original editing request" in prompt
    assert "Deterministic compliance findings" in prompt
    assert "**Draft headline:** Attend Tumbbad" in prompt
    assert "[composition_title_format]" in prompt
    assert "needs one" in prompt
    assert "repair pass" in prompt
