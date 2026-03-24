"""Tests for Submission CRUD endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import make_submission_data


@pytest.mark.asyncio
class TestSubmissionCRUD:
    async def test_create_submission(self, client: AsyncClient):
        data = make_submission_data()
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert body["Original_Headline"] == data["Original_Headline"]
        assert body["Category"] == "faculty_staff"
        assert body["Status"] == "new"
        assert body["Id"]

    async def test_create_submission_with_links(self, client: AsyncClient):
        data = make_submission_data(
            Links=[{"Url": "https://example.com", "Anchor_Text": "Example"}]
        )
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["Links"]) == 1
        assert body["Links"][0]["Url"] == "https://example.com"

    async def test_create_submission_with_schedule(self, client: AsyncClient):
        data = make_submission_data(
            Schedule_Requests=[{"Requested_Date": "2026-03-15", "Repeat_Count": 2}]
        )
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["Schedule_Requests"]) == 1
        assert body["Schedule_Requests"][0]["Repeat_Count"] == 2

    async def test_create_submission_with_second_requested_date(
        self, client: AsyncClient
    ):
        data = make_submission_data(
            Target_Newsletter="both",
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-13",
                    "Second_Requested_Date": "2026-03-16",
                    "Repeat_Count": 2,
                }
            ],
        )
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 201
        schedule = resp.json()["Schedule_Requests"][0]
        assert schedule["Repeat_Count"] == 2
        assert schedule["Second_Requested_Date"] == "2026-03-16"

    async def test_create_submission_persists_survey_end_date(self, client: AsyncClient):
        data = make_submission_data(
            Category="survey",
            Survey_End_Date="2026-04-15",
        )
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 201
        assert resp.json()["Survey_End_Date"] == "2026-04-15"

    async def test_create_submission_with_recurring_schedule(self, client: AsyncClient):
        data = make_submission_data(
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-02",
                    "Recurrence_Type": "monthly_nth_weekday",
                    "Recurrence_Interval": 1,
                    "Recurrence_End_Date": "2026-06-01",
                }
            ]
        )
        resp = await client.post(
            "/api/v1/submissions/",
            json=data,
            headers={"X-User-Role": "staff"},
        )
        assert resp.status_code == 201
        schedule = resp.json()["Schedule_Requests"][0]
        assert schedule["Recurrence_Type"] == "monthly_nth_weekday"
        assert schedule["Recurrence_End_Date"] == "2026-06-01"
        assert schedule["Occurrence_Dates"] == [
            "2026-04-06",
            "2026-05-04",
            "2026-06-01",
        ]
        assert resp.json()["Occurrence_Dates"] == [
            "2026-04-06",
            "2026-05-04",
            "2026-06-01",
        ]

    async def test_public_submitter_cannot_create_recurring_schedule(
        self, client: AsyncClient
    ):
        data = make_submission_data(
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-02",
                    "Recurrence_Type": "monthly_nth_weekday",
                    "Recurrence_Interval": 1,
                    "Recurrence_End_Date": "2026-06-01",
                }
            ]
        )
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 403
        assert "staff editors only" in resp.json()["detail"]

    async def test_public_submitter_cannot_use_staff_only_category(self, client: AsyncClient):
        data = make_submission_data(Category="news_release")
        resp = await client.post("/api/v1/submissions/", json=data)
        assert resp.status_code == 422
        assert "not available" in resp.json()["detail"]

    async def test_staff_submitter_can_use_staff_only_category(self, client: AsyncClient):
        data = make_submission_data(Category="news_release")
        resp = await client.post(
            "/api/v1/submissions/",
            json=data,
            headers={"X-User-Role": "staff"},
        )
        assert resp.status_code == 201
        assert resp.json()["Category"] == "news_release"

    async def test_list_submissions(self, client: AsyncClient):
        # Create two submissions
        await client.post("/api/v1/submissions/", json=make_submission_data())
        await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(Original_Headline="Second one"),
        )
        resp = await client.get("/api/v1/submissions/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["Total"] == 2
        assert len(body["Items"]) == 2

    async def test_list_submissions_filter_status(self, client: AsyncClient):
        await client.post("/api/v1/submissions/", json=make_submission_data())
        resp = await client.get("/api/v1/submissions/?status=new")
        assert resp.status_code == 200
        assert resp.json()["Total"] == 1

        resp = await client.get("/api/v1/submissions/?status=approved")
        assert resp.json()["Total"] == 0

    async def test_list_submissions_includes_recurring_occurrences_in_range(
        self, client: AsyncClient
    ):
        recurring = make_submission_data(
            Original_Headline="Recurring feature",
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-02",
                    "Recurrence_Type": "monthly_nth_weekday",
                    "Recurrence_Interval": 1,
                    "Recurrence_End_Date": "2026-06-01",
                }
            ],
        )
        one_off = make_submission_data(
            Original_Headline="One off",
            Schedule_Requests=[{"Requested_Date": "2026-03-15"}],
        )

        await client.post(
            "/api/v1/submissions/",
            json=recurring,
            headers={"X-User-Role": "staff"},
        )
        await client.post("/api/v1/submissions/", json=one_off)

        resp = await client.get(
            "/api/v1/submissions/?date_from=2026-04-01&date_to=2026-04-30"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["Total"] == 1
        assert body["Items"][0]["Original_Headline"] == "Recurring feature"
        assert body["Items"][0]["Occurrence_Dates"] == ["2026-04-06"]

    async def test_get_submission(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.get(f"/api/v1/submissions/{sub_id}")
        assert resp.status_code == 200
        assert resp.json()["Id"] == sub_id

    async def test_get_submission_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/submissions/nonexistent")
        assert resp.status_code == 404

    async def test_update_submission(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.patch(
            f"/api/v1/submissions/{sub_id}",
            json={"Status": "approved"},
        )
        assert resp.status_code == 200
        assert resp.json()["Status"] == "approved"

    async def test_update_submission_survey_end_date(self, client: AsyncClient):
        create_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(Category="survey"),
        )
        sub_id = create_resp.json()["Id"]

        resp = await client.patch(
            f"/api/v1/submissions/{sub_id}",
            json={"Survey_End_Date": "2026-05-01"},
        )
        assert resp.status_code == 200
        assert resp.json()["Survey_End_Date"] == "2026-05-01"

    async def test_staff_can_update_editorial_workflow_fields(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.patch(
            f"/api/v1/submissions/{sub_id}",
            json={
                "Assigned_Editor": "Jane Editor",
                "Editorial_Notes": "Waiting on quote confirmation.",
            },
            headers={"X-User-Role": "staff"},
        )
        assert resp.status_code == 200
        assert resp.json()["Assigned_Editor"] == "Jane Editor"
        assert resp.json()["Editorial_Notes"] == "Waiting on quote confirmation."

    async def test_public_cannot_update_editorial_workflow_fields(
        self, client: AsyncClient
    ):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.patch(
            f"/api/v1/submissions/{sub_id}",
            json={"Assigned_Editor": "Jane Editor"},
        )
        assert resp.status_code == 403
        assert "Only staff editors" in resp.json()["detail"]

    async def test_public_list_redacts_editorial_workflow_fields(
        self, client: AsyncClient
    ):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]
        await client.patch(
            f"/api/v1/submissions/{sub_id}",
            json={
                "Assigned_Editor": "Jane Editor",
                "Editorial_Notes": "Internal note.",
            },
            headers={"X-User-Role": "staff"},
        )

        public_resp = await client.get("/api/v1/submissions/")
        assert public_resp.status_code == 200
        item = public_resp.json()["Items"][0]
        assert item["Assigned_Editor"] is None
        assert item["Editorial_Notes"] is None

        staff_resp = await client.get(
            "/api/v1/submissions/",
            headers={"X-User-Role": "staff"},
        )
        assert staff_resp.status_code == 200
        staff_item = staff_resp.json()["Items"][0]
        assert staff_item["Assigned_Editor"] == "Jane Editor"
        assert staff_item["Editorial_Notes"] == "Internal note."

    async def test_delete_submission(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/submissions/{sub_id}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/submissions/{sub_id}")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestSubmissionLinks:
    async def test_add_link(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/submissions/{sub_id}/links",
            json={"Url": "https://test.com", "Anchor_Text": "Test"},
        )
        assert resp.status_code == 201
        assert resp.json()["Url"] == "https://test.com"

    async def test_delete_link(self, client: AsyncClient):
        data = make_submission_data(
            Links=[{"Url": "https://delete-me.com", "Anchor_Text": "Delete"}]
        )
        create_resp = await client.post("/api/v1/submissions/", json=data)
        link_id = create_resp.json()["Links"][0]["Id"]
        sub_id = create_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/submissions/{sub_id}/links/{link_id}")
        assert resp.status_code == 204


@pytest.mark.asyncio
class TestSubmissionSchedule:
    async def test_add_schedule_request(self, client: AsyncClient):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/submissions/{sub_id}/schedule",
            json={"Requested_Date": "2026-04-01", "Repeat_Count": 2},
        )
        assert resp.status_code == 201
        assert resp.json()["Repeat_Count"] == 2

    async def test_public_submitter_cannot_add_recurring_schedule_request(
        self, client: AsyncClient
    ):
        create_resp = await client.post("/api/v1/submissions/", json=make_submission_data())
        sub_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/submissions/{sub_id}/schedule",
            json={
                "Requested_Date": "2026-04-06",
                "Recurrence_Type": "weekly",
                "Recurrence_Interval": 1,
            },
        )
        assert resp.status_code == 403
        assert "staff editors only" in resp.json()["detail"]

    async def test_delete_schedule_request(self, client: AsyncClient):
        data = make_submission_data(
            Schedule_Requests=[{"Requested_Date": "2026-05-01", "Repeat_Count": 1}]
        )
        create_resp = await client.post("/api/v1/submissions/", json=data)
        sched_id = create_resp.json()["Schedule_Requests"][0]["Id"]
        sub_id = create_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/submissions/{sub_id}/schedule/{sched_id}")
        assert resp.status_code == 204

    async def test_skip_schedule_occurrence(self, client: AsyncClient):
        data = make_submission_data(
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-02",
                    "Recurrence_Type": "monthly_nth_weekday",
                    "Recurrence_Interval": 1,
                    "Recurrence_End_Date": "2026-06-01",
                }
            ]
        )
        create_resp = await client.post(
            "/api/v1/submissions/",
            json=data,
            headers={"X-User-Role": "staff"},
        )
        sched_id = create_resp.json()["Schedule_Requests"][0]["Id"]
        sub_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/submissions/{sub_id}/schedule/{sched_id}/skip",
            json={"Occurrence_Date": "2026-04-06"},
            headers={"X-User-Role": "staff"},
        )
        assert resp.status_code == 200
        assert resp.json()["Excluded_Dates"] == ["2026-04-06"]
        assert resp.json()["Occurrence_Dates"] == ["2026-05-04", "2026-06-01"]

        list_resp = await client.get(
            "/api/v1/submissions/?date_from=2026-04-01&date_to=2026-04-30"
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["Total"] == 0

    async def test_reschedule_schedule_occurrence(self, client: AsyncClient):
        data = make_submission_data(
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-02",
                    "Recurrence_Type": "monthly_nth_weekday",
                    "Recurrence_Interval": 1,
                    "Recurrence_End_Date": "2026-06-01",
                }
            ]
        )
        create_resp = await client.post(
            "/api/v1/submissions/",
            json=data,
            headers={"X-User-Role": "staff"},
        )
        sched_id = create_resp.json()["Schedule_Requests"][0]["Id"]
        sub_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/submissions/{sub_id}/schedule/{sched_id}/reschedule",
            json={
                "Occurrence_Date": "2026-04-06",
                "New_Date": "2026-04-08",
            },
            headers={"X-User-Role": "staff"},
        )
        assert resp.status_code == 201
        assert resp.json()["Requested_Date"] == "2026-04-08"
        assert resp.json()["Occurrence_Dates"] == ["2026-04-08"]

        list_resp = await client.get(
            "/api/v1/submissions/?date_from=2026-04-01&date_to=2026-04-30"
        )
        assert list_resp.status_code == 200
        body = list_resp.json()
        assert body["Total"] == 1
        assert body["Items"][0]["Occurrence_Dates"] == ["2026-04-08"]

    async def test_public_submitter_cannot_skip_occurrence(self, client: AsyncClient):
        data = make_submission_data(
            Schedule_Requests=[
                {
                    "Requested_Date": "2026-03-02",
                    "Recurrence_Type": "monthly_nth_weekday",
                    "Recurrence_Interval": 1,
                    "Recurrence_End_Date": "2026-06-01",
                }
            ]
        )
        create_resp = await client.post(
            "/api/v1/submissions/",
            json=data,
            headers={"X-User-Role": "staff"},
        )
        sched_id = create_resp.json()["Schedule_Requests"][0]["Id"]
        sub_id = create_resp.json()["Id"]

        resp = await client.post(
            f"/api/v1/submissions/{sub_id}/schedule/{sched_id}/skip",
            json={"Occurrence_Date": "2026-04-06"},
        )
        assert resp.status_code == 403
        assert "staff editors" in resp.json()["detail"]
