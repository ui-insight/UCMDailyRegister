"""Tests for StyleRule CRUD endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import make_style_rule_data


@pytest.mark.asyncio
class TestStyleRuleCRUD:
    async def test_create_style_rule(self, client: AsyncClient, staff_headers: dict[str, str]):
        data = make_style_rule_data()
        resp = await client.post("/api/v1/style-rules", json=data, headers=staff_headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["Rule_Key"] == "test_rule"
        assert body["Is_Active"] is True
        assert body["Id"]

    async def test_list_style_rules(self, client: AsyncClient, staff_headers: dict[str, str]):
        await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(Rule_Key="r1"),
            headers=staff_headers,
        )
        await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(Rule_Key="r2"),
            headers=staff_headers,
        )

        resp = await client.get("/api/v1/style-rules")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    async def test_list_style_rules_filter_rule_set(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(Rule_Set="shared", Rule_Key="s1"),
            headers=staff_headers,
        )
        await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(Rule_Set="tdr", Rule_Key="t1"),
            headers=staff_headers,
        )

        resp = await client.get("/api/v1/style-rules?rule_set=tdr")
        assert resp.status_code == 200
        rules = resp.json()
        assert len(rules) == 1
        assert rules[0]["Rule_Set"] == "tdr"

    async def test_get_style_rule(self, client: AsyncClient, staff_headers: dict[str, str]):
        create_resp = await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(),
            headers=staff_headers,
        )
        rule_id = create_resp.json()["Id"]

        resp = await client.get(f"/api/v1/style-rules/{rule_id}")
        assert resp.status_code == 200
        assert resp.json()["Id"] == rule_id

    async def test_get_style_rule_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/style-rules/nonexistent")
        assert resp.status_code == 404

    async def test_update_style_rule(self, client: AsyncClient, staff_headers: dict[str, str]):
        create_resp = await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(),
            headers=staff_headers,
        )
        rule_id = create_resp.json()["Id"]

        resp = await client.patch(
            f"/api/v1/style-rules/{rule_id}",
            json={"Rule_Text": "Updated rule text", "Severity": "error"},
            headers=staff_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["Rule_Text"] == "Updated rule text"
        assert resp.json()["Severity"] == "error"

    async def test_deactivate_style_rule(
        self, client: AsyncClient, staff_headers: dict[str, str]
    ):
        create_resp = await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(),
            headers=staff_headers,
        )
        rule_id = create_resp.json()["Id"]

        resp = await client.patch(
            f"/api/v1/style-rules/{rule_id}",
            json={"Is_Active": False},
            headers=staff_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["Is_Active"] is False

    async def test_delete_style_rule(self, client: AsyncClient, staff_headers: dict[str, str]):
        create_resp = await client.post(
            "/api/v1/style-rules",
            json=make_style_rule_data(),
            headers=staff_headers,
        )
        rule_id = create_resp.json()["Id"]

        resp = await client.delete(f"/api/v1/style-rules/{rule_id}", headers=staff_headers)
        assert resp.status_code == 204

        resp = await client.get(f"/api/v1/style-rules/{rule_id}")
        assert resp.status_code == 404
