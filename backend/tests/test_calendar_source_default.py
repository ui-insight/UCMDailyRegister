"""The default calendar source is the public Trumba RSS feed."""

from app.config import Settings


def test_default_calendar_source_is_public_trumba_rss(monkeypatch):
    monkeypatch.delenv("CALENDAR_SOURCE_URL", raising=False)
    url = Settings(_env_file=None).calendar_source_url
    assert url == "https://www.trumba.com/calendars/university-of-idaho.rss"
    assert "qatrumba" not in url
