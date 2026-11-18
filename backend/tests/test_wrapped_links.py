"""Email security wrappers are replaced with the real URL before the AI sees the text (#530).

All addresses here are synthetic.
"""

from datetime import datetime, timezone
from urllib.parse import quote

import pytest

from app.models.submission import Submission, SubmissionLink
from app.schemas.submission import LinkCreate
from app.services.ai.editor import AIEditor
from app.utils.hyperlinks import (
    WRAPPED_LINK_NOTE,
    is_wrapped_url,
    resolve_tracking_url,
    unwrap_links_in_text,
)

REAL = "https://forms.example.com/r/AbC123"
V3_SINGLE_SLASH = "urldefense.com/v3/__https:/forms.example.com/r/AbC123__;!!JYXjzlvb!abcDEF$"
V3 = "https://urldefense.com/v3/__https://forms.example.com/r/AbC123__;!!JYXjzlvb!abcDEF$"
V3_PLACEHOLDER = "https://urldefense.com/v3/__https://forms.example.com/r/A*C123__;Yg!!JYXjzlvb!abc$"
V3_CUT_OFF = "https://urldefense.com/v3/__https://forms.example.com/r/Ab"
SAFE_LINKS = (
    "https://nam12.safelinks.protection.outlook.com/?url="
    + quote("https://events.example.edu/fair?id=7&ref=mail", safe="")
    + "&data=05%7C02%7Cperson%40example.edu%7Cabc&sdata=xyz&reserved=0"
)
MIMECAST_OPAQUE = "https://protect-us.mimecast.com/s/AbCdEfGhIj?domain=example.edu"


@pytest.mark.parametrize(
    ("wrapped", "real"),
    [
        # Joy's example: take what's between "__" and "__;", restore "//".
        (V3_SINGLE_SLASH, REAL),
        (V3, REAL),
        (SAFE_LINKS, "https://events.example.edu/fair?id=7&ref=mail"),
        (
            "https://safelinks.protection.outlook.com/?url=https%3A%2F%2Fexample.edu%2Fa&data=x",
            "https://example.edu/a",
        ),
        (
            "https://urldefense.proofpoint.com/v2/url?u=https-3A__example.edu_page&d=x",
            "https://example.edu/page",
        ),
        (
            "https://linkprotect.cudasvc.com/url?a=https%3A%2F%2Fexample.edu%2Fb&c=E",
            "https://example.edu/b",
        ),
    ],
)
def test_wrapped_links_resolve_to_the_real_destination(wrapped, real):
    assert is_wrapped_url(wrapped)
    assert resolve_tracking_url(wrapped) == real


@pytest.mark.parametrize(
    "wrapped",
    [
        V3_PLACEHOLDER,
        V3_CUT_OFF,
        MIMECAST_OPAQUE,
        "https://nam12.safelinks.protection.outlook.com/?data=05%7Cabc",
        "https://urldefense.com/v3/__forms.example.com__;!!x$",
    ],
)
def test_unrecoverable_wrappers_are_not_guessed(wrapped):
    assert resolve_tracking_url(wrapped) is None


@pytest.mark.parametrize(
    "url",
    ["https://example.edu/page", "mailto:person@example.edu", "https://notsafelinks.example.com/x"],
)
def test_unwrapped_links_pass_through(url):
    assert not is_wrapped_url(url)
    assert resolve_tracking_url(url) == url


def test_text_wrappers_are_replaced_and_unrecoverable_ones_removed():
    text = (
        f"Fill out <a href=\"{V3}\">the form</a>, see {SAFE_LINKS}. "
        f"Or use <a href=\"{V3_PLACEHOLDER}\">this link</a> or {V3_CUT_OFF} today."
    )
    unwrapped, lost = unwrap_links_in_text(text)
    assert unwrapped == (
        f"Fill out <a href=\"{REAL}\">the form</a>, see "
        "https://events.example.edu/fair?id=7&ref=mail. Or use this link or today."
    )
    assert lost == ["this link", V3_CUT_OFF]
    assert "urldefense" not in unwrapped and "safelinks" not in unwrapped


def test_text_without_wrappers_is_unchanged():
    text = 'Visit <a href="https://example.edu">the site</a> or https://example.edu/b.'
    assert unwrap_links_in_text(text) == (text, [])


def test_submitted_link_fields_store_the_real_destination():
    assert LinkCreate(Url=V3_SINGLE_SLASH).Url == REAL
    assert LinkCreate(Url=SAFE_LINKS).Url == "https://events.example.edu/fair?id=7&ref=mail"
    # Unrecoverable: kept as submitted so the AI edit can flag it.
    assert LinkCreate(Url=V3_PLACEHOLDER).Url == V3_PLACEHOLDER


@pytest.mark.asyncio
async def test_the_model_never_sees_a_wrapper_and_lost_links_are_flagged():
    calls = []

    class ScriptedProvider:
        model = "scripted"

        async def complete_json(self, **kwargs):
            calls.append(kwargs)
            return {
                "edited_headline": "Example fair",
                "edited_body": f'Fill out <a href="{REAL}">the form</a> today.',
                "flags": [],
            }

    class Editor(AIEditor):
        async def load_style_rules(self, session, newsletter_type):
            return []

    submission = Submission(
        Id="synthetic",
        Category="faculty_staff",
        Target_Newsletter="tdr",
        Original_Headline="Example fair",
        Original_Body=f"Fill out the form at {V3_SINGLE_SLASH} today.",
        Submitter_Notes=f"Also link {SAFE_LINKS}",
        Submitter_Name="Synthetic",
        Submitter_Email="synthetic@example.edu",
        Created_At=datetime(2026, 11, 17, 9, tzinfo=timezone.utc),
        Links=[
            SubmissionLink(Url=REAL, Anchor_Text="the form"),
            SubmissionLink(Url=V3_PLACEHOLDER, Anchor_Text="Register now"),
        ],
    )
    result = await Editor(ScriptedProvider()).edit_submission(None, submission, "tdr")

    (call,) = calls
    prompt = call["user_prompt"]
    assert "urldefense" not in prompt and "safelinks" not in prompt
    assert REAL in prompt
    assert "https://events.example.edu/fair?id=7&ref=mail" in prompt
    lost = [flag for flag in result.flags if WRAPPED_LINK_NOTE in flag["message"]]
    assert lost == [
        {
            "type": "warning",
            "rule_key": "link_embedding",
            "message": (
                f"{WRAPPED_LINK_NOTE}: 'Register now' was left unlinked because the real "
                "address behind the email security wrapper couldn't be recovered"
            ),
        }
    ]
    # The stored submission is unchanged.
    assert submission.Original_Body == f"Fill out the form at {V3_SINGLE_SLASH} today."
