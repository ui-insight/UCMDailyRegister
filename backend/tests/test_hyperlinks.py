"""Tests for hyperlink parsing and URL unwrapping utilities."""

import pytest

from app.utils.hyperlinks import (
    ParsedLink,
    _clean_url,
    extract_urls_from_body,
    parse_submitter_notes,
    unwrap_tracking_url,
)


class TestUnwrapTrackingUrl:
    """Test unwrapping of email security gateway tracking URLs."""

    def test_proofpoint_v3(self):
        wrapped = "https://urldefense.com/v3/__https://basecamp.qualtrics.com/jfe/form/SV_abc123__;!!JYXjzlQ!example"
        assert unwrap_tracking_url(wrapped) == "https://basecamp.qualtrics.com/jfe/form/SV_abc123"

    def test_proofpoint_v3_proofpoint_domain(self):
        wrapped = "https://urldefense.proofpoint.com/v3/__https://www.uidaho.edu/events__;!!abc"
        assert unwrap_tracking_url(wrapped) == "https://www.uidaho.edu/events"

    def test_proofpoint_v2(self):
        # v2 encoding: colons → hyphens, slashes → underscores
        wrapped = "https://urldefense.proofpoint.com/v2/url?u=https-3A__www.uidaho.edu_events&d=DwMF&c=abc"
        assert unwrap_tracking_url(wrapped) == "https://www.uidaho.edu/events"

    def test_microsoft_safe_links(self):
        wrapped = "https://safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.uidaho.edu%2Fevents&data=05&sdata=abc"
        assert unwrap_tracking_url(wrapped) == "https://www.uidaho.edu/events"

    def test_microsoft_safe_links_complex(self):
        wrapped = "https://safelinks.protection.outlook.com/?url=https%3A%2F%2Fbasecamp.qualtrics.com%2Fjfe%2Fform%2FSV_abc123&data=05"
        assert unwrap_tracking_url(wrapped) == "https://basecamp.qualtrics.com/jfe/form/SV_abc123"

    def test_mimecast(self):
        wrapped = "https://protect-us.mimecast.com/s/https://www.uidaho.edu/events/"
        assert unwrap_tracking_url(wrapped) == "https://www.uidaho.edu/events"

    def test_mimecast_eu(self):
        wrapped = "https://protect-eu.mimecast.com/s/https://www.uidaho.edu/"
        assert unwrap_tracking_url(wrapped) == "https://www.uidaho.edu"

    def test_barracuda(self):
        wrapped = "https://linkprotect.cudasvc.com/url?a=https%3A%2F%2Fwww.uidaho.edu%2Fevents&c=E"
        assert unwrap_tracking_url(wrapped) == "https://www.uidaho.edu/events"

    def test_normal_url_passthrough(self):
        url = "https://www.uidaho.edu/events"
        assert unwrap_tracking_url(url) == url

    def test_normal_url_with_params_passthrough(self):
        url = "https://example.com/page?foo=bar&baz=1"
        assert unwrap_tracking_url(url) == url

    def test_empty_string(self):
        assert unwrap_tracking_url("") == ""

    def test_non_http_passthrough(self):
        url = "ftp://files.example.com/data"
        assert unwrap_tracking_url(url) == url


class TestCleanUrl:
    def test_strips_trailing_punctuation(self):
        assert _clean_url("https://example.com/page.") == "https://example.com/page"
        assert _clean_url("https://example.com/page,") == "https://example.com/page"

    def test_unwraps_and_strips(self):
        wrapped = "https://safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.uidaho.edu&data=05."
        # trailing dot stripped first, then unwrapped
        result = _clean_url(wrapped)
        assert result == "https://www.uidaho.edu"


class TestParseSubmitterNotesWithTracking:
    """Ensure tracking URLs are unwrapped during note parsing."""

    def test_wrapped_url_in_link_instruction(self):
        notes = 'Link "Register" to https://urldefense.com/v3/__https://example.com/register__;!!abc'
        links = parse_submitter_notes(notes)
        assert len(links) == 1
        assert links[0].url == "https://example.com/register"
        assert links[0].anchor_text == "Register"

    def test_wrapped_bare_url(self):
        notes = "Check out https://safelinks.protection.outlook.com/?url=https%3A%2F%2Fwww.uidaho.edu&data=05"
        links = parse_submitter_notes(notes)
        assert len(links) == 1
        assert links[0].url == "https://www.uidaho.edu"

    def test_mixed_wrapped_and_normal(self):
        notes = (
            "Link to https://urldefense.com/v3/__https://example.com__;!!abc "
            "and also https://www.uidaho.edu"
        )
        links = parse_submitter_notes(notes)
        urls = {link.url for link in links}
        assert "https://example.com" in urls
        assert "https://www.uidaho.edu" in urls


class TestExtractUrlsFromBodyWithTracking:
    def test_wrapped_url_in_body(self):
        body = "Visit https://urldefense.com/v3/__https://www.uidaho.edu/events__;!!xyz for details."
        links = extract_urls_from_body(body)
        assert len(links) == 1
        assert links[0].url == "https://www.uidaho.edu/events"
        assert links[0].source == "body_text"
