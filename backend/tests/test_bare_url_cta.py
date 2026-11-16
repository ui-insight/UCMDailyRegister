"""A repeated URL never shows as text or link text; the CTA words carry the link (#478).

Joy's rules: (1) when the body repeats a link-field URL, drop the written-out
URL and rework the sentence so the call-to-action words carry the link;
(2) never show a URL as link text, and link each URL once per item; (3) one
URL with one CTA is a single call to action, even when the CTA names more
than one action. All text here is synthetic.
"""

import importlib.util
import json
from pathlib import Path

import pytest
import sqlalchemy as sa
from httpx import AsyncClient

from app.evals.editorial import SeedRulesEditor, load_cases, score, seed_rules
from app.models.submission import Submission, SubmissionLink
from app.services.ai.prompts import build_edit_user_prompt, build_system_prompt
from app.utils.body_links import link_key
from app.utils.link_repair import (
    CTA_LINK_DESCRIPTION,
    REPAIR_DESCRIPTION,
    link_problems,
    repair_links,
)
from app.utils.style_checks import detect_missing_information_options
from tests.conftest import make_submission_data

URL = "https://www.uidaho.edu/example-event"
CTA = "Learn more and sign up"
LINKS = [{"url": URL, "anchor_text": CTA}]
LEAD = "The Example Club meets at 4 p.m. Friday, Nov. 20, in the Example Hall. "
LINKED_CTA = f'<a href="{URL}">{CTA}</a>.'


def linked(words: str, url: str = URL) -> str:
    return f'<a href="{url}">{words}</a>'


class TestLinkKey:
    @pytest.mark.parametrize(
        "variant",
        [
            "http://www.uidaho.edu/example-event",
            "https://uidaho.edu/example-event/",
            "https://WWW.UIDaho.edu/example-event",
            "www.uidaho.edu/example-event",
            "https://www.uidaho.edu/example-event.",
        ],
    )
    def test_same_page_compares_equal(self, variant):
        assert link_key(variant) == link_key(URL)

    def test_different_pages_differ(self):
        assert link_key("https://www.uidaho.edu/other-event") != link_key(URL)
        assert link_key(f"{URL}?day=2") != link_key(URL)


class TestRepairedCases:
    """Rule 1: the repeated URL goes and the CTA words carry the one link."""

    @pytest.mark.parametrize(
        "body",
        [
            # The reported shape: the URL is the link text.
            f"{LEAD}Learn more and sign up at {linked(URL)}.",
            # Split CTA, URL written out with another scheme and a slash.
            f"{LEAD}{linked('Learn more')} and sign up at http://uidaho.edu/example-event/.",
            # The same page linked twice on halves of the CTA.
            f"{LEAD}{linked('Learn more')} and {linked('sign up')}.",
            # The URL splits the CTA words mid-sentence.
            f"{LEAD}Learn more at www.uidaho.edu/example-event and sign up.",
            # The CTA isn't linked and the URL follows "online at".
            f"{LEAD}Learn more and sign up online at {URL}.",
            # "here:" before the URL.
            f"{LEAD}Learn more and sign up here: {URL}.",
        ],
    )
    def test_cta_carries_the_only_link(self, body):
        repaired, notes = repair_links(body, LINKS)

        assert repaired == f"{LEAD}{LINKED_CTA}"
        assert notes
        assert link_problems(repaired) == []

    @pytest.mark.parametrize(
        "pointer",
        [
            f"Visit {URL}.",
            f"For more information, visit {URL}.",
            f"More information is available at {URL}.",
            f"See the event page at {URL}.",
            f"{URL}.",
        ],
    )
    def test_sentence_that_only_points_at_the_url_is_removed(self, pointer):
        body = f"{LEAD}{LINKED_CTA} {pointer} Snacks are provided."

        repaired, notes = repair_links(body, LINKS)

        assert repaired == f"{LEAD}{LINKED_CTA} Snacks are provided."
        assert notes == [REPAIR_DESCRIPTION]

    def test_pointer_sentence_at_the_end_is_removed(self):
        repaired, _ = repair_links(f"{LEAD}{LINKED_CTA} Visit {URL}", LINKS)
        assert repaired == f"{LEAD}{LINKED_CTA}"

    def test_url_in_parentheses_is_removed(self):
        repaired, _ = repair_links(f"{LEAD}{linked(CTA)} ({URL}).", LINKS)
        assert repaired == f"{LEAD}{LINKED_CTA}"

    def test_body_link_without_link_field_still_drops_the_copy(self):
        body = f"{LEAD}{linked('Register')} at {URL} by Nov. 18."

        repaired, notes = repair_links(body, [])

        assert repaired == f"{LEAD}{linked('Register')} by Nov. 18."
        assert notes == [REPAIR_DESCRIPTION]

    def test_unlinked_cta_words_get_the_link(self):
        repaired, notes = repair_links(f"{LEAD}Learn more and sign up.", LINKS)

        assert repaired == f"{LEAD}{LINKED_CTA}"
        assert notes == [CTA_LINK_DESCRIPTION]

    def test_curly_apostrophe_in_body_matches_straight_cta(self):
        links = [{"url": URL, "anchor_text": "Reserve the club's table"}]
        body = f"{LEAD}Reserve the club’s table at {URL}."

        repaired, _ = repair_links(body, links)

        assert repaired == f"{LEAD}{linked('Reserve the club’s table')}."

    def test_other_links_are_copied_through_exactly(self):
        other = "<a href='mailto:club@example.edu' title='x'>the club</a>"
        body = f"{LEAD}Learn more and sign up at {linked(URL)}. Questions go to {other}."

        repaired, _ = repair_links(body, LINKS)

        assert repaired == f"{LEAD}{LINKED_CTA} Questions go to {other}."

    def test_correct_body_is_unchanged(self):
        body = f"{LEAD}{LINKED_CTA}"
        assert repair_links(body, LINKS) == (body, [])


class TestFlaggedCases:
    """When the sentence can't be reworked safely, the text stays and staff get a flag."""

    def test_url_mid_sentence_after_a_verb_is_flagged(self):
        body = f"{LEAD}Visit {URL} to {linked('learn more and sign up')}."

        repaired, notes = repair_links(body, LINKS)

        assert (repaired, notes) == (body, [])
        assert link_problems(repaired) == [
            f"Web address '{URL}' repeats the link on 'learn more and sign up'. "
            "Remove it and rework the sentence."
        ]

    def test_url_link_text_without_cta_words_is_flagged_not_lost(self):
        body = f"{LEAD}Register at {linked(URL)}."

        repaired, notes = repair_links(body, [{"url": URL, "anchor_text": "Reserve a seat"}])

        assert (repaired, notes) == (body, [])
        assert link_problems(repaired) == [
            f"Link text is a web address: '{URL}'. Link the call-to-action words instead."
        ]

    def test_cta_is_not_linked_twice(self):
        body = f"{LEAD}{linked('Register')} today. Learn more and sign up."

        repaired, _ = repair_links(body, LINKS)

        assert repaired == body

    def test_same_page_linked_twice_is_flagged(self):
        body = f"{LEAD}{linked('Register')} today. {linked('See the schedule')}."
        assert link_problems(body) == [f"'{URL}' is linked 2 times. Link it once."]

    def test_unrelated_written_out_url_is_flagged_not_removed(self):
        body = f"{LEAD}{LINKED_CTA} The map is at https://www.uidaho.edu/example-map."

        assert repair_links(body, LINKS) == (body, [])
        assert link_problems(body) == [
            "Web address written out as text: 'https://www.uidaho.edu/example-map'. "
            "Link descriptive words instead, unless UCM is running the address as written."
        ]


class TestInformationOptions:
    """Rule 3: one URL with one CTA is a single call to action."""

    def test_multi_action_cta_on_one_linked_url_is_not_flagged(self):
        source = f"{LEAD}Learn more and sign up at {URL}."
        assert detect_missing_information_options(source, f"{LEAD}{linked('Sign up')}.") == []

    def test_option_is_still_flagged_when_the_link_is_gone(self):
        source = f"{LEAD}Learn more and sign up at {URL}."
        assert detect_missing_information_options(source, f"{LEAD}Sign up.") == ["Learn more"]

    def test_separate_contact_option_is_still_flagged(self):
        source = f"{LEAD}Sign up at {URL}. Questions? Email the club office."
        assert detect_missing_information_options(source, f"{LEAD}{linked('Sign up')}.") == [
            "Questions"
        ]


def submission(body: str, links: list[dict]) -> Submission:
    return Submission(
        Id="synthetic-478",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="Join the Example Club",
        Original_Body=body,
        Submitter_Name="Synthetic Submitter",
        Submitter_Email="submitter@example.edu",
        Links=[
            SubmissionLink(Url=link["url"], Anchor_Text=link["anchor_text"], Display_Order=i)
            for i, link in enumerate(links)
        ],
    )


class ScriptedLLM:
    model = "scripted"

    def __init__(self, body: str):
        self.body = body
        self.prompts: list[tuple[str, str]] = []

    async def complete_json(self, *, system_prompt, user_prompt, **_kwargs):
        self.prompts.append((system_prompt, user_prompt))
        return {
            "edited_headline": "Join the Example Club",
            "edited_body": self.body,
            "changes_made": [],
            "flags": [],
            "embedded_links": [{"url": URL, "anchor_text": URL}],
            "confidence": 0.9,
        }


@pytest.mark.asyncio
class TestPipeline:
    async def test_ai_edit_returns_one_link_on_the_cta(self):
        source = f"{LEAD}Learn more and sign up at {URL}."
        llm = ScriptedLLM(f"{LEAD}{linked('Learn more')} and sign up at {linked(URL)}.")

        result = await SeedRulesEditor(llm).edit_submission(None, submission(source, LINKS), "tdr")

        assert result.edited_body == f"{LEAD}{LINKED_CTA}"
        assert REPAIR_DESCRIPTION in result.changes_made
        link_flags = [f for f in result.flags if f["rule_key"] == "link_embedding"]
        assert link_flags == []
        assert not [f for f in result.flags if f["rule_key"] == "preserve_information_options"]

    async def test_unresolved_url_is_flagged_for_staff(self):
        body = f"{LEAD}Visit {URL} to {linked('learn more and sign up')}."
        llm = ScriptedLLM(body)

        result = await SeedRulesEditor(llm).edit_submission(None, submission(body, LINKS), "tdr")

        assert URL in result.edited_body
        assert any(
            f["rule_key"] == "link_embedding" and "repeats the link" in f["message"]
            for f in result.flags
        )

    async def test_switching_off_link_rule_leaves_body_alone(self):
        body = f"{LEAD}Learn more and sign up at {linked(URL)}."

        class NoLinkRule(SeedRulesEditor):
            async def load_style_rules(self, session, newsletter_type):
                rules = await super().load_style_rules(session, newsletter_type)
                return [r for r in rules if r["rule_key"] != "link_embedding"]

        result = await NoLinkRule(ScriptedLLM(body)).edit_submission(
            None, submission(body, LINKS), "tdr"
        )

        assert linked(URL) in result.edited_body
        assert REPAIR_DESCRIPTION not in result.changes_made


class TestPromptAndRules:
    def test_system_prompt_states_the_link_rules(self):
        prompt = build_system_prompt("tdr", seed_rules("tdr"), "faculty_staff")
        assert "Never use a URL as anchor text" in prompt
        assert "Link each URL only once" in prompt
        assert "One URL with one call to action is a single call to action" in prompt
        assert "remove the written-out URL" in prompt

    def test_user_prompt_marks_provided_links(self):
        prompt = build_edit_user_prompt(
            headline="Join", body=f"Sign up at {URL}.", submitter_notes=None,
            links=LINKS, category="faculty_staff",
        )
        assert "if the body repeats the URL, remove it from the body" in prompt
        assert f'- "{CTA}" → {URL}' in prompt

    def test_information_options_rule_no_longer_asks_to_split_one_cta(self):
        rules = {rule["rule_key"]: rule for rule in seed_rules("tdr")}
        text = rules["preserve_information_options"]["rule_text"]
        assert "If readers may sign up or learn more, retain both" not in text
        assert "One URL with one call to action is a single call to action" in text
        assert "link each URL only once" in rules["link_embedding"]["rule_text"]


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "b3d5f7a9c1e4_keep_one_link_on_cta_words.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location("keep_one_link", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigration:
    def test_matches_seeds(self):
        seeded = {
            rule["rule_key"]: rule
            for rule in json.loads(
                (Path(__file__).parents[1] / "data" / "style_rules" / "shared_rules.json")
                .read_text(encoding="utf-8")
            )
        }
        for rule_key, category, rule_text, severity in load_migration().RULES:
            assert seeded[rule_key]["rule_text"] == rule_text
            assert seeded[rule_key]["category"] == category
            assert seeded[rule_key]["severity"] == severity

    def test_upsert_is_idempotent_and_keeps_staff_choices(self):
        migration = load_migration()
        engine = sa.create_engine("sqlite://")
        metadata = sa.MetaData()
        rules = sa.Table(
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
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(rules.insert(), [
                {"Id": "old", "Rule_Set": "shared", "Category": "formatting",
                 "Rule_Key": "link_embedding", "Rule_Text": "Old.",
                 "Is_Active": False, "Severity": "warning"},
                {"Id": "staff", "Rule_Set": "shared", "Category": "voice",
                 "Rule_Key": "staff_custom", "Rule_Text": "Keep me.",
                 "Is_Active": True, "Severity": "info"},
            ])
            migration._upsert_rules(connection)
            migration._upsert_rules(connection)
            rows = {
                row["Rule_Key"]: row
                for row in connection.execute(sa.select(rules)).mappings().all()
            }

        assert len(rows) == 3
        assert rows["staff_custom"]["Rule_Text"] == "Keep me."
        assert rows["link_embedding"]["Is_Active"] is False  # staff switched it off
        assert "link each URL only once" in rows["link_embedding"]["Rule_Text"]
        assert rows["preserve_information_options"]["Is_Active"] is True


def test_eval_case_scores_the_link():
    case = next(c for c in load_cases() if c["id"] == "repeated-url-cta-carries-link")
    good = f"{LEAD}{LINKED_CTA}"
    bad = f"{LEAD}{linked('Learn more')} and sign up at {linked(URL)}."

    assert all(check.passed for check in score(case, "Join", good, []))
    assert not all(check.passed for check in score(case, "Join", bad, []))


@pytest.mark.asyncio
async def test_final_edit_keeps_a_url_staff_put_back(
    client: AsyncClient,
    staff_headers: dict[str, str],
):
    """UCM sometimes runs the URL as written; staff restore it in Final Edit."""
    created = await client.post(
        "/api/v1/submissions/",
        json=make_submission_data(
            Original_Body=f"Learn more and sign up at {URL}.",
            Links=[{"Url": URL, "Anchor_Text": CTA}],
        ),
    )
    body = f"{linked(CTA)} at {URL}."

    final = await client.post(
        f"/api/v1/ai-edits/{created.json()['Id']}/finalize",
        json={"Headline": "Join the Example Club", "Body": body},
        headers=staff_headers,
    )

    assert final.status_code == 200
    assert final.json()["Body"] == body
