"""Tests for AllowedValue read-only endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.allowed_value import AllowedValue


@pytest.mark.asyncio
class TestAllowedValues:
    async def _seed_values(self, db: AsyncSession):
        """Seed a few AllowedValue rows for testing."""
        await db.execute(delete(AllowedValue))
        values = [
            AllowedValue(
                Value_Group="Submission_Category",
                Code="faculty_staff",
                Label="Faculty/Staff",
                Display_Order=1,
                Is_Active=True,
                Visibility_Role="public",
            ),
            AllowedValue(
                Value_Group="Submission_Category",
                Code="student",
                Label="Student",
                Display_Order=2,
                Is_Active=True,
                Visibility_Role="public",
            ),
            AllowedValue(
                Value_Group="Submission_Category",
                Code="news_release",
                Label="News Release",
                Display_Order=3,
                Is_Active=True,
                Visibility_Role="staff",
            ),
            AllowedValue(
                Value_Group="Newsletter_Type",
                Code="tdr",
                Label="The Daily Register",
                Display_Order=1,
                Is_Active=True,
                Visibility_Role="public",
            ),
            AllowedValue(
                Value_Group="Submission_Category",
                Code="deprecated",
                Label="Deprecated Category",
                Display_Order=99,
                Is_Active=False,
                Visibility_Role="public",
            ),
        ]
        db.add_all(values)
        await db.commit()

    async def test_list_by_group(self, client: AsyncClient, db: AsyncSession):
        await self._seed_values(db)

        resp = await client.get("/api/v1/allowed-values?group=Submission_Category")
        assert resp.status_code == 200
        items = resp.json()
        # Only active values by default
        assert len(items) == 2
        assert all(v["Value_Group"] == "Submission_Category" for v in items)
        assert all(v["Visibility_Role"] == "public" for v in items)

    async def test_list_submission_categories_for_staff(
        self, client: AsyncClient, db: AsyncSession, staff_headers: dict[str, str]
    ):
        await self._seed_values(db)

        resp = await client.get(
            "/api/v1/allowed-values?group=Submission_Category",
            headers=staff_headers,
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3
        assert items[-1]["Code"] == "news_release"

    async def test_list_includes_inactive(self, client: AsyncClient, db: AsyncSession):
        await self._seed_values(db)

        resp = await client.get("/api/v1/allowed-values?group=Submission_Category&active_only=false")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3  # Includes deprecated

    async def test_list_different_group(self, client: AsyncClient, db: AsyncSession):
        await self._seed_values(db)

        resp = await client.get("/api/v1/allowed-values?group=Newsletter_Type")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["Code"] == "tdr"

    async def test_list_all_groups(self, client: AsyncClient, db: AsyncSession):
        await self._seed_values(db)

        resp = await client.get("/api/v1/allowed-values")
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3  # 3 active values across all groups

    async def test_response_shape(self, client: AsyncClient, db: AsyncSession):
        await self._seed_values(db)

        resp = await client.get("/api/v1/allowed-values?group=Newsletter_Type")
        item = resp.json()[0]
        assert "Id" in item
        assert "Value_Group" in item
        assert "Code" in item
        assert "Label" in item
        assert "Display_Order" in item
        assert "Is_Active" in item
        assert "Visibility_Role" in item
