"""Submissions record which signed-in account sent them.

All identities and content here are synthetic.
"""

import pytest
import sqlalchemy as sa
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps as auth_deps
from app.auth.session_tokens import create_session_token
from app.models.submission import Submission
from tests.conftest import make_submission_data

SUBMITTER_OID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_OID = "99999999-8888-4777-8666-555555555555"


def _bearer(role: str, oid: str | None) -> dict[str, str]:
    token = create_session_token(
        subject="synthetic-submitter@example.test",
        role=role,  # type: ignore[arg-type]
        name="Synthetic Submitter",
        object_id=oid,
    )
    return {"Authorization": f"Bearer {token}"}


async def _stored_ref(db: AsyncSession, submission_id: str) -> str | None:
    db.expire_all()
    return await db.scalar(
        sa.select(Submission.Submitter_Account_Ref).where(Submission.Id == submission_id)
    )


@pytest.fixture
def oidc_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth_deps.settings, "auth_provider", "oidc")


@pytest.mark.asyncio
@pytest.mark.usefixtures("oidc_mode")
class TestUnderSso:
    async def test_signed_in_submitter_oid_is_recorded(
        self, client: AsyncClient, db: AsyncSession
    ):
        resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
            headers=_bearer("submitter", SUBMITTER_OID),
        )
        assert resp.status_code == 201
        assert await _stored_ref(db, resp.json()["Id"]) == SUBMITTER_OID

    async def test_request_body_cannot_set_the_reference(
        self, client: AsyncClient, db: AsyncSession
    ):
        body = make_submission_data() | {"Submitter_Account_Ref": OTHER_OID}
        resp = await client.post(
            "/api/v1/submissions/", json=body, headers=_bearer("submitter", SUBMITTER_OID)
        )
        assert resp.status_code == 201
        assert await _stored_ref(db, resp.json()["Id"]) == SUBMITTER_OID

    async def test_reference_is_not_returned_to_callers(self, client: AsyncClient):
        created = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
            headers=_bearer("submitter", SUBMITTER_OID),
        )
        assert "Submitter_Account_Ref" not in created.json()
        assert SUBMITTER_OID not in created.text

        staff = _bearer("staff", OTHER_OID)
        detail = await client.get(f"/api/v1/submissions/{created.json()['Id']}", headers=staff)
        listing = await client.get("/api/v1/submissions/", headers=staff)
        assert SUBMITTER_OID not in detail.text
        assert SUBMITTER_OID not in listing.text

    async def test_session_without_oid_records_null(
        self, client: AsyncClient, db: AsyncSession
    ):
        resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
            headers=_bearer("submitter", None),
        )
        assert resp.status_code == 201
        assert await _stored_ref(db, resp.json()["Id"]) is None


@pytest.mark.asyncio
async def test_header_mode_records_null(client: AsyncClient, db: AsyncSession):
    resp = await client.post("/api/v1/submissions/", json=make_submission_data())
    assert resp.status_code == 201
    assert await _stored_ref(db, resp.json()["Id"]) is None
