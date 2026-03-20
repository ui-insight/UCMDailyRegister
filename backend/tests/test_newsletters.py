"""Tests for Newsletter CRUD and assembly endpoints."""

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.section import NewsletterSection
from app.services import calendar_event_service, job_posting_service
from tests.conftest import make_newsletter_data, make_submission_data


@pytest.mark.asyncio
class TestNewsletterCRUD:
    async def test_create_newsletter(self, client: AsyncClient):
        resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        assert resp.status_code == 201
        body = resp.json()
        assert body["Newsletter_Type"] == "tdr"
        assert body["Status"] == "draft"
        assert body["Id"]

    async def test_list_newsletters(self, client: AsyncClient):
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Publish_Date="2026-03-01"))
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Publish_Date="2026-03-02"))

        resp = await client.get("/api/v1/newsletters")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_newsletters_filter_type(self, client: AsyncClient):
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Newsletter_Type="tdr"))
        await client.post("/api/v1/newsletters", json=make_newsletter_data(Newsletter_Type="myui"))

        resp = await client.get("/api/v1/newsletters?newsletter_type=myui")
        assert resp.status_code == 200
        nls = resp.json()
        assert len(nls) == 1
        assert nls[0]["Newsletter_Type"] == "myui"

    async def test_get_newsletter(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.get(f"/api/v1/newsletters/{nl_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["Id"] == nl_id
        assert "Items" in body

    async def test_update_newsletter_status(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.patch(f"/api/v1/newsletters/{nl_id}/status?status=in_progress")
        assert resp.status_code == 200
        assert resp.json()["Status"] == "in_progress"

    async def test_delete_newsletter(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/newsletters/{nl_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/newsletters/{nl_id}")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestNewsletterItems:
    async def test_add_item(self, client: AsyncClient):
        # Create newsletter and submission
        nl_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = nl_resp.json()["Id"]
        sub_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = sub_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/items",
            json={
                "Submission_Id": sub_id,
                "Section_Id": "fake-section-id",
                "Position": 0,
                "Final_Headline": "Test headline",
                "Final_Body": "Test body",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["Final_Headline"] == "Test headline"

    async def test_remove_item(self, client: AsyncClient):
        nl_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = nl_resp.json()["Id"]
        sub_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = sub_resp.json()["Id"]

        item_resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/items",
            json={
                "Submission_Id": sub_id,
                "Section_Id": "sec-1",
                "Position": 0,
                "Final_Headline": "Remove me",
                "Final_Body": "Body",
            },
        )
        item_id = item_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/newsletters/{nl_id}/items/{item_id}")
        assert resp.status_code == 204

    async def test_assemble_newsletter_uses_matching_recurring_occurrence(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        db.add(
            NewsletterSection(
                Newsletter_Type="tdr",
                Name="Employee News",
                Slug="employee-news",
                Display_Order=1,
                Is_Active=True,
            )
        )
        await db.commit()

        recurring_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Headline="Recurring feature",
                Schedule_Requests=[
                    {
                        "Requested_Date": "2026-03-02",
                        "Recurrence_Type": "monthly_nth_weekday",
                        "Recurrence_Interval": 1,
                        "Recurrence_End_Date": "2026-06-01",
                    }
                ],
            ),
            headers={"X-User-Role": "staff"},
        )
        recurring_id = recurring_resp.json()["Id"]
        await client.patch(
            f"/api/v1/submissions/{recurring_id}",
            json={"Status": "approved"},
        )

        one_off_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(
                Original_Headline="Wrong date",
                Schedule_Requests=[{"Requested_Date": "2026-04-07"}],
            ),
        )
        one_off_id = one_off_resp.json()["Id"]
        await client.patch(
            f"/api/v1/submissions/{one_off_id}",
            json={"Status": "approved"},
        )

        assemble_resp = await client.post(
            "/api/v1/newsletters/assemble",
            json={"Newsletter_Type": "tdr", "Publish_Date": "2026-04-06"},
        )
        assert assemble_resp.status_code == 200
        items = assemble_resp.json()["Items"]
        assert len(items) == 1
        assert items[0]["Submission_Id"] == recurring_id


class TestCalendarEventParsing:
    def test_parse_trumba_hcalendar(self):
        html = """
        <html><body>
          <h2><a href="/event-1">Accessibility Workshop</a></h2>
          <p>Learn how to build accessible documents. University Location: IRIC 305.
          Thursday, March 19, 2026, 12:00 PM - 1:00 PM. For more info visit
          <a href="https://www.uidaho.edu/event-1">event page</a>.</p>
          <h2>Contact Us</h2>
        </body></html>
        """

        events = calendar_event_service.parse_trumba_hcalendar(
            html,
            "https://calendar.example.test",
        )

        assert len(events) == 1
        event = events[0]
        assert event.title == "Accessibility Workshop"
        assert event.location == "IRIC 305"
        assert event.url == "https://www.uidaho.edu/event-1"
        assert event.event_start == datetime(2026, 3, 19, 12, 0)


class TestJobPostingParsing:
    def test_parse_peopleadmin_search_results(self):
        html = """
        <div class='job-item job-item-posting' data-posting-title="Business Specialist III">
          <div class='container-fluid'>
            <div class='row'>
              <div class='col-md-4 col-xs-12 job-title job-title-text-wrap'>
                <h3><a href="/postings/50999">Business Specialist III</a></h3>
              </div>
              <div class='col-md-8 col-xs-12 '>
                <div class='col-md-2 col-xs-12'></div>
                <div class='col-md-2 col-xs-12 job-title job-title-text-wrap col-md-push-2'>
                  College of Natural Resources Admin
                </div>
                <div class='col-md-2 col-xs-12 job-title job-title-text-wrap col-md-push-2'>
                  04/05/2026
                </div>
                <div class='col-md-2 col-xs-12 job-title job-title-text-wrap col-md-push-2'>
                  SP005197P
                </div>
                <div class='col-md-2 col-xs-12 job-title job-title-text-wrap col-md-push-2'>
                  Moscow
                </div>
              </div>
            </div>
            <div class='row'>
              <div class='col-md-12 col-xs-12'>
                <div class='details'>
                  <span class='job-description'>
                    Responsible for providing complex technical support for daily financial operations.
                  </span>
                  <span class='job-actions'>
                    <a class="btn primary_button_color" href="/postings/50999">View Details</a>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div role="navigation" aria-label="Pagination" class="pagination"></div>
        """

        postings = job_posting_service.parse_peopleadmin_search_results(
            html,
            "https://uidaho.peopleadmin.com/postings/search",
        )

        assert len(postings) == 1
        posting = postings[0]
        assert posting.title == "Business Specialist III"
        assert posting.department == "College of Natural Resources Admin"
        assert posting.posting_number == "SP005197P"
        assert posting.location == "Moscow"
        assert posting.closing_date == "04/05/2026"
        assert posting.url == "https://uidaho.peopleadmin.com/postings/50999"


@pytest.mark.asyncio
class TestCalendarEventEndpoints:
    async def test_list_calendar_event_candidates(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        async def fake_fetch_calendar_events(*args, **kwargs):
            return [{
                "Source_Id": "event-1",
                "Source_Type": "calendar_event",
                "Url": "https://example.com/event-1",
                "Title": "Accessibility Workshop",
                "Description": "Learn accessible PDF output.",
                "Location": "IRIC 305",
                "Event_Start": datetime(2026, 3, 19, 12, 0),
                "Event_End": datetime(2026, 3, 19, 13, 0),
                "Selected": False,
            }]

        monkeypatch.setattr(
            calendar_event_service,
            "fetch_calendar_events",
            fake_fetch_calendar_events,
        )

        resp = await client.get(f"/api/v1/newsletters/{nl_id}/calendar-events")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["Source_Id"] == "event-1"

    async def test_import_calendar_event(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        db.add(
            NewsletterSection(
                Newsletter_Type="tdr",
                Name="Today's Events",
                Slug="todays-events",
                Display_Order=4,
                Is_Active=True,
            )
        )
        await db.commit()

        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/calendar-events",
            json={
                "Source_Id": "event-1",
                "Url": "https://example.com/event-1",
                "Title": "Accessibility Workshop",
                "Description": "Learn accessible PDF output.",
                "Location": "IRIC 305",
                "Event_Start": "2026-03-19T12:00:00",
                "Event_End": "2026-03-19T13:00:00",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["Source_Type"] == "calendar_event"
        assert body["Final_Headline"] == "Accessibility Workshop"

        detail_resp = await client.get(f"/api/v1/newsletters/{nl_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["External_Items"]) == 1


@pytest.mark.asyncio
class TestJobPostingEndpoints:
    async def test_list_job_posting_candidates(
        self,
        client: AsyncClient,
        monkeypatch: pytest.MonkeyPatch,
    ):
        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        async def fake_fetch_job_postings(*args, **kwargs):
            return [{
                "Source_Id": "https://example.com/postings/1",
                "Source_Type": "job_posting",
                "Url": "https://example.com/postings/1",
                "Title": "Business Specialist III",
                "Department": "College of Natural Resources Admin",
                "Posting_Number": "SP005197P",
                "Location": "Moscow",
                "Closing_Date": "04/05/2026",
                "Summary": "Responsible for providing complex technical support.",
                "Selected": False,
            }]

        monkeypatch.setattr(
            job_posting_service,
            "fetch_job_postings",
            fake_fetch_job_postings,
        )

        resp = await client.get(f"/api/v1/newsletters/{nl_id}/job-postings")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["Source_Type"] == "job_posting"

    async def test_import_job_posting(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        db.add(
            NewsletterSection(
                Newsletter_Type="tdr",
                Name="Job Opportunities",
                Slug="job-opportunities",
                Display_Order=8,
                Is_Active=True,
            )
        )
        await db.commit()

        create_resp = await client.post("/api/v1/newsletters", json=make_newsletter_data())
        nl_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/newsletters/{nl_id}/job-postings",
            json={
                "Source_Id": "https://example.com/postings/1",
                "Url": "https://example.com/postings/1",
                "Title": "Business Specialist III",
                "Department": "College of Natural Resources Admin",
                "Posting_Number": "SP005197P",
                "Location": "Moscow",
                "Closing_Date": "04/05/2026",
                "Summary": "Responsible for providing complex technical support.",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["Source_Type"] == "job_posting"
        assert "Business Specialist III" in body["Final_Headline"]

        detail_resp = await client.get(f"/api/v1/newsletters/{nl_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert len(detail["External_Items"]) == 1
