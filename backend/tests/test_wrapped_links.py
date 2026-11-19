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


def test_percent_encoded_destinations_are_decoded_only_once():
    # PR #533 review: Barracuda's parameter was decoded twice.
    wrapped = "https://linkprotect.cudasvc.com/url?a=https%3A%2F%2Fexample.com%2F%253Fname%253Dx"
    assert resolve_tracking_url(wrapped) == "https://example.com/%3Fname%3Dx"
    safe_links = "https://nam12.safelinks.protection.outlook.com/?url=https%3A%2F%2Fexample.com%2F%253Fa&data=x"
    assert resolve_tracking_url(safe_links) == "https://example.com/%3Fa"


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


# Regional Safe Links hosts and look-alikes (#520). All addresses synthetic.


def _safe_links(host: str, target: str) -> str:
    return f"https://{host}/?url={quote(target, safe='')}&data=05%7C02%7Cx&sdata=y&reserved=0"


@pytest.mark.parametrize(
    "host",
    [
        "nam12.safelinks.protection.outlook.com",
        "eur03.safelinks.protection.outlook.com",
        "gcc02.safelinks.protection.outlook.com",
        "apc01.safelinks.protection.outlook.com",
        "NAM02.SafeLinks.Protection.Outlook.com",
    ],
)
def test_regional_safe_links_hosts_are_unwrapped(host):
    wrapped = _safe_links(host, "https://news.example.edu/story?id=42")
    assert is_wrapped_url(wrapped)
    assert resolve_tracking_url(wrapped) == "https://news.example.edu/story?id=42"


@pytest.mark.parametrize(
    "url",
    [
        _safe_links("safelinks.protection.outlook.com.evil.example", "https://news.example.edu/a"),
        _safe_links("nam12.safelinks.protection.outlook.com.evil.example", "https://news.example.edu/a"),
        _safe_links("evilsafelinks.protection.outlook.com", "https://news.example.edu/a"),
        _safe_links("safelinks-protection-outlook.example.com", "https://news.example.edu/a"),
        "https://evil.example/nam12.safelinks.protection.outlook.com/?url=https%3A%2F%2Fnews.example.edu",
    ],
)
def test_look_alike_hosts_are_not_unwrapped(url):
    assert not is_wrapped_url(url)
    assert resolve_tracking_url(url) == url


def test_look_alike_in_text_is_left_alone():
    look_alike = (
        "https://evil.example/safelinks.protection.outlook.com/?url=https%3A%2F%2Fnews.example.edu&data=1"
    )
    text = f"See {look_alike} today."
    assert unwrap_links_in_text(text) == (text, [])


def test_double_encoded_safe_links_target_is_decoded():
    wrapped = (
        "https://gcc02.safelinks.protection.outlook.com/?url="
        "https%253A%252F%252Fnews.example.edu%252Fstory&data=x"
    )
    assert resolve_tracking_url(wrapped) == "https://news.example.edu/story"


def test_safe_links_around_proofpoint_unwraps_both_layers():
    inner = "https://urldefense.com/v3/__https://forms.example.com/r/AbC123__;!!JYXjzlvb!abc$"
    wrapped = _safe_links("eur03.safelinks.protection.outlook.com", inner)
    assert resolve_tracking_url(wrapped) == REAL


def test_wrapper_nesting_is_bounded():
    url = "https://news.example.edu/a"
    for _ in range(5):
        url = _safe_links("nam12.safelinks.protection.outlook.com", url)
    assert resolve_tracking_url(url) is None


def test_proofpoint_v3_target_containing_double_underscore():
    wrapped = (
        "https://urldefense.com/v3/__https://files.example.com/a__b/report__v2.pdf__;!!JYXjzlvb!abc$"
    )
    assert resolve_tracking_url(wrapped) == "https://files.example.com/a__b/report__v2.pdf"


def test_text_with_several_regional_links():
    first = _safe_links("nam12.safelinks.protection.outlook.com", "https://one.example.edu/a")
    second = _safe_links("eur03.safelinks.protection.outlook.com", "https://two.example.edu/b?x=1&y=2")
    third = _safe_links("gcc02.safelinks.protection.outlook.com", "https://three.example.edu/")
    text = f'Register at <a href="{first}">this page</a>. Details: {second}, and Link:{third}'
    unwrapped, lost = unwrap_links_in_text(text)
    assert lost == []
    assert unwrapped == (
        'Register at <a href="https://one.example.edu/a">this page</a>. '
        "Details: https://two.example.edu/b?x=1&y=2, and Link:https://three.example.edu/"
    )
