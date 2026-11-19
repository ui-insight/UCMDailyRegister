"""Word export format and layout (#535, #536), on a synthetic newsletter."""

import io
import re
import zipfile
from datetime import date

import pytest
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.newsletter import Newsletter, NewsletterExternalItem
from app.models.section import NewsletterSection
from app.utils.ap_dates import ap_date
from app.utils.export import SECTION_HEADING_STYLE, export_newsletter_docx

FOOTER_TEXT = "University of Idaho | University Communications and Marketing"

JOBS = [
    ("Business manager II, Chemistry", "https://uidaho.example/jobs/1"),
    ("Events technical coordinator, Auxiliary Services", "https://uidaho.example/jobs/2"),
    ("Research scientist, Example Lab", "https://uidaho.example/jobs/3"),
]


def _job_body(text: str, href: str) -> str:
    return f'<a href="{href}">{text}</a>'


SECTIONS = [
    {
        "name": "Employee News",
        "items": [
            {"Final_Headline": "Library extends hours", "Final_Body": "The library is open late."},
            {"Final_Headline": "Benefits fair", "Final_Body": "Visit the fair on Nov. 20."},
        ],
    },
    {
        "name": "Job Opportunities",
        "compact": True,
        "items": [{"Final_Headline": None, "Final_Body": _job_body(*job)} for job in JOBS],
    },
    {"name": "Events", "items": [], "empty_text": "No events."},
]


def _export(publish_date: date = date(2026, 11, 18), sections=SECTIONS) -> bytes:
    return export_newsletter_docx("tdr", publish_date, sections).getvalue()


def _paragraph_hrefs(document, paragraph) -> list[str]:
    rels = document.part.rels
    return [rels[h.get(qn("r:id"))].target_ref for h in paragraph._p.iter(qn("w:hyperlink"))]


def _paragraph_text(paragraph) -> str:
    return "".join(t.text or "" for t in paragraph._p.iter(qn("w:t")))


class TestCompatibilityMode:
    def test_settings_declare_current_word_format(self):
        with zipfile.ZipFile(io.BytesIO(_export())) as package:
            settings = package.read("word/settings.xml").decode()
        modes = re.findall(r'<w:compatSetting [^>]*w:name="compatibilityMode"[^>]*/>', settings)
        assert len(modes) == 1
        assert 'w:val="15"' in modes[0]


class TestApDate:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (date(2026, 11, 18), "Nov. 18, 2026"),
            (date(2026, 3, 3), "March 3, 2026"),
            (date(2026, 9, 1), "Sept. 1, 2026"),
            (date(2026, 7, 4), "July 4, 2026"),
            (date(2027, 1, 5), "Jan. 5, 2027"),
        ],
    )
    def test_ap_date(self, value: date, expected: str):
        assert ap_date(value) == expected

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (date(2026, 11, 18), "Nov. 18, 2026"),
            (date(2026, 3, 3), "March 3, 2026"),
            (date(2026, 9, 1), "Sept. 1, 2026"),
        ],
    )
    def test_export_date_line(self, value: date, expected: str):
        document = Document(io.BytesIO(_export(value)))
        texts = [p.text for p in document.paragraphs]
        assert expected in texts
        assert not any("day," in t for t in texts[:3])  # no weekday


class TestJobsSection:
    def _job_paragraphs(self, document):
        paragraphs = document.paragraphs
        start = next(i for i, p in enumerate(paragraphs) if p.text == "Job Opportunities")
        return paragraphs[start + 1 : start + 1 + len(JOBS)]

    def test_jobs_are_consecutive_tight_paragraphs_with_links(self):
        document = Document(io.BytesIO(_export()))
        job_paragraphs = self._job_paragraphs(document)
        assert [_paragraph_text(p) for p in job_paragraphs] == [text for text, _ in JOBS]
        for paragraph, (_, href) in zip(job_paragraphs, JOBS):
            assert _paragraph_hrefs(document, paragraph) == [href]
            assert paragraph.paragraph_format.space_before == Pt(0)
            assert paragraph.paragraph_format.space_after == Pt(0)

    def test_other_sections_keep_their_spacer_paragraphs(self):
        document = Document(io.BytesIO(_export()))
        texts = [p.text for p in document.paragraphs]
        first = texts.index("The library is open late.")
        assert texts[first + 1] == ""
        assert texts[first + 2] == "Benefits fair"


class TestFontSize:
    def test_normal_style_is_14pt(self):
        document = Document(io.BytesIO(_export()))
        assert document.styles["Normal"].font.size == Pt(14)

    def test_explicit_headline_and_body_runs_are_14pt(self):
        document = Document(io.BytesIO(_export()))
        sized = [
            run
            for p in document.paragraphs
            if p.text in {"Library extends hours", "The library is open late."}
            for run in p.runs
        ]
        assert sized
        assert all(run.font.size == Pt(14) for run in sized)

    def test_hyperlink_runs_are_14pt(self):
        document = Document(io.BytesIO(_export()))
        sizes = {
            sz.get(qn("w:val"))
            for h in document.element.body.iter(qn("w:hyperlink"))
            for sz in h.iter(qn("w:sz"))
        }
        assert sizes == {"28"}


def test_footer_is_gone():
    document = Document(io.BytesIO(_export()))
    texts = [p.text for p in document.paragraphs]
    assert FOOTER_TEXT not in texts
    assert texts[-1] == ""  # only the spacer after the last section remains
    assert texts[-2] == "No events."


class TestSectionHeadings:
    def test_headings_use_plain_style_without_outline_level(self):
        document = Document(io.BytesIO(_export()))
        headings = [
            p for p in document.paragraphs
            if p.text in {"Employee News", "Job Opportunities", "Events"}
        ]
        assert len(headings) == 3
        for paragraph in headings:
            assert paragraph.style.name == SECTION_HEADING_STYLE
            assert paragraph._p.find(f".//{qn('w:outlineLvl')}") is None

    def test_no_paragraph_carries_an_outline_level(self):
        document = Document(io.BytesIO(_export()))
        for paragraph in document.paragraphs:
            assert not paragraph.style.name.lower().startswith("heading")
            style = paragraph.style
            while style is not None:
                assert style.element.find(f".//{qn('w:outlineLvl')}") is None
                style = style.base_style

    def test_heading_style_keeps_the_look(self):
        style = Document(io.BytesIO(_export())).styles[SECTION_HEADING_STYLE]
        assert style.font.bold is True
        assert str(style.font.color.rgb) == "8C6E1A"
        assert style.font.size == Pt(16)


@pytest.mark.asyncio
async def test_export_route_lists_jobs_tightly(
    client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
):
    news = NewsletterSection(
        Newsletter_Type="tdr", Name="Employee News", Slug="employee-news", Display_Order=1, Is_Active=True
    )
    jobs = NewsletterSection(
        Newsletter_Type="tdr",
        Name="Job Opportunities",
        Slug="job-opportunities",
        Display_Order=2,
        Is_Active=True,
    )
    newsletter = Newsletter(Newsletter_Type="tdr", Publish_Date=date(2026, 9, 1), Status="draft")
    db.add_all([news, jobs, newsletter])
    await db.flush()
    for position, (text, href) in enumerate(JOBS[:2]):
        db.add(
            NewsletterExternalItem(
                Newsletter_Id=newsletter.Id,
                Section_Id=jobs.Id,
                Source_Type="job_posting",
                Source_Id=f"job-{position}",
                Position=position,
                Final_Headline="",
                Final_Body=_job_body(text, href),
            )
        )
    db.add(
        NewsletterExternalItem(
            Newsletter_Id=newsletter.Id,
            Section_Id=news.Id,
            Source_Type="recurring_message",
            Source_Id="news-1",
            Position=0,
            Final_Headline="A news item",
            Final_Body="Some news.",
        )
    )
    await db.commit()

    resp = await client.get(f"/api/v1/newsletters/{newsletter.Id}/export", headers=staff_headers)
    assert resp.status_code == 200
    document = Document(io.BytesIO(resp.content))
    texts = [p.text for p in document.paragraphs]
    assert "Sept. 1, 2026" in texts
    start = texts.index("Job Opportunities")
    job_paragraphs = document.paragraphs[start + 1 : start + 3]
    assert [_paragraph_text(p) for p in job_paragraphs] == [text for text, _ in JOBS[:2]]
    assert all(p.paragraph_format.space_after == Pt(0) for p in job_paragraphs)
    news_index = texts.index("Some news.")
    assert texts[news_index + 1] == ""
