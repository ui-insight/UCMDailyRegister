"""Order of items within a Builder section, and the same order in the export (#509).

Submissions and imported items (events, jobs, recurring messages, academic
dates) share one position sequence per section. All data here is synthetic.
"""

import io

import pytest
from docx import Document
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.newsletter import NewsletterExternalItem, NewsletterItem
from app.models.section import NewsletterSection
from app.services import newsletter_service
from tests.conftest import make_newsletter_data, make_submission_data

PUBLISH_DATE = "2026-04-06"


@pytest.fixture
async def employee_news(db: AsyncSession) -> str:
    db.add_all([
        NewsletterSection(
            Id="tdr-employee-news",
            Newsletter_Type="tdr",
            Name="Employee News",
            Slug="employee-news",
            Display_Order=1,
            Is_Active=True,
        ),
        NewsletterSection(
            Id="tdr-events",
            Newsletter_Type="tdr",
            Name="Upcoming events",
            Slug="todays-events",
            Display_Order=2,
            Is_Active=True,
        ),
    ])
    await db.commit()
    return "tdr-employee-news"


async def _newsletter(client: AsyncClient, headers: dict[str, str]) -> str:
    resp = await client.post(
        "/api/v1/newsletters",
        json=make_newsletter_data(Publish_Date=PUBLISH_DATE),
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["Id"]


async def _import(db: AsyncSession, newsletter_id: str, section_id: str, headline: str) -> str:
    item = await newsletter_service.add_external_item(
        db,
        newsletter_id=newsletter_id,
        section_id=section_id,
        source_type="recurring_message",
        source_id=f"source-{headline}",
        source_url=None,
        event_start=None,
        event_end=None,
        location=None,
        final_headline=headline,
        final_body=f"{headline} body.",
    )
    return item.Id


async def _approved_submission(client: AsyncClient, headers: dict[str, str], headline: str) -> str:
    resp = await client.post(
        "/api/v1/submissions/",
        json=make_submission_data(
            Original_Headline=headline,
            Schedule_Requests=[{"Requested_Date": PUBLISH_DATE}],
        ),
        headers=headers,
    )
    submission_id = resp.json()["Id"]
    await client.patch(
        f"/api/v1/submissions/{submission_id}",
        json={"Status": "approved"},
        headers=headers,
    )
    return submission_id


def _section_order(detail: dict, section_id: str) -> list[str]:
    """Headlines in the Builder's order: the backend's section_order_key."""
    items = [
        item
        for item in (*detail["Items"], *detail["External_Items"])
        if item["Section_Id"] == section_id
    ]
    items.sort(key=lambda item: (item["Position"], item["Final_Headline"], item["Id"]))
    return [item["Final_Headline"] for item in items]


@pytest.mark.asyncio
class TestBuilderOrder:
    async def test_imports_into_an_empty_section_get_consecutive_positions(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str], employee_news: str,
    ):
        newsletter_id = await _newsletter(client, staff_headers)
        for headline in ("First", "Second", "Third", "Fourth"):
            await _import(db, newsletter_id, employee_news, headline)

        detail = (await client.get(f"/api/v1/newsletters/{newsletter_id}", headers=staff_headers)).json()
        positions = {item["Final_Headline"]: item["Position"] for item in detail["External_Items"]}
        assert positions == {"First": 0, "Second": 1, "Third": 2, "Fourth": 3}

    async def test_assembly_places_a_submission_after_imported_items(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str], employee_news: str,
    ):
        newsletter_id = await _newsletter(client, staff_headers)
        await _import(db, newsletter_id, employee_news, "Zebra reminder")
        await _import(db, newsletter_id, employee_news, "Yak reminder")
        await _approved_submission(client, staff_headers, "Aardvark news")

        resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": PUBLISH_DATE},
            headers=staff_headers,
        )
        assert resp.status_code == 200
        assert _section_order(resp.json(), employee_news) == [
            "Zebra reminder", "Yak reminder", "Aardvark news",
        ]

    async def test_moving_a_submission_keeps_its_place_among_imported_items(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str], employee_news: str,
    ):
        newsletter_id = await _newsletter(client, staff_headers)
        reminder_id = await _import(db, newsletter_id, employee_news, "Reminder")
        await _approved_submission(client, staff_headers, "Story A")
        await _approved_submission(client, staff_headers, "Story B")
        detail = (await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": PUBLISH_DATE},
            headers=staff_headers,
        )).json()
        assert _section_order(detail, employee_news) == ["Reminder", "Story A", "Story B"]
        ids = {item["Final_Headline"]: item["Id"] for item in detail["Items"]}

        # Move Story B to the top, ahead of the imported reminder.
        resp = await client.put(
            f"/api/v1/newsletters/{newsletter_id}/reorder",
            json=[
                {"Id": ids["Story B"], "Position": 0, "Section_Id": employee_news},
                {"Id": reminder_id, "Position": 1},
                {"Id": ids["Story A"], "Position": 2, "Section_Id": employee_news},
            ],
            headers=staff_headers,
        )
        assert resp.status_code == 200

        detail = (await client.get(f"/api/v1/newsletters/{newsletter_id}", headers=staff_headers)).json()
        assert _section_order(detail, employee_news) == ["Story B", "Reminder", "Story A"]
        positions = sorted(
            item["Position"]
            for item in (*detail["Items"], *detail["External_Items"])
            if item["Section_Id"] == employee_news
        )
        assert positions == [0, 1, 2]

    async def test_export_order_matches_builder_order_when_positions_tie(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str], employee_news: str,
    ):
        """Data written before the fix can still hold ties; both views break them alike."""
        newsletter_id = await _newsletter(client, staff_headers)
        submission_id = await _approved_submission(client, staff_headers, "Zulu story")
        db.add_all([
            NewsletterItem(
                Newsletter_Id=newsletter_id,
                Submission_Id=submission_id,
                Section_Id=employee_news,
                Final_Headline="Zulu story",
                Final_Body="Zulu body.",
                Position=0,
            ),
            NewsletterExternalItem(
                Newsletter_Id=newsletter_id,
                Section_Id=employee_news,
                Source_Type="recurring_message",
                Source_Id="alpha",
                Final_Headline="Alpha reminder",
                Final_Body="Alpha body.",
                Position=0,
            ),
        ])
        await db.commit()

        detail = (await client.get(f"/api/v1/newsletters/{newsletter_id}", headers=staff_headers)).json()
        builder_order = _section_order(detail, employee_news)
        assert builder_order == ["Alpha reminder", "Zulu story"]

        resp = await client.get(f"/api/v1/newsletters/{newsletter_id}/export", headers=staff_headers)
        assert resp.status_code == 200
        text = "\n".join(p.text for p in Document(io.BytesIO(resp.content)).paragraphs)
        assert text.index("Alpha reminder") < text.index("Zulu story")
