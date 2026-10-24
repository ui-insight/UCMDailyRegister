"""Reopen task state in a fresh interpreter against a synthetic on-disk DB."""

import json
import os
from pathlib import Path
import subprocess
import sys


def test_fresh_backend_process_preserves_results_and_recovers_pending_tasks(tmp_path):
    env = {
        "PATH": os.defpath,
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        "DATABASE_URL": f"sqlite+aiosqlite:///{tmp_path}/synthetic.db",
        "AUTH_PROVIDER": "header",
        "ENVIRONMENT": "development",
        "CORS_ORIGINS": "http://localhost:5173",
        "UPLOAD_DIR": str(tmp_path / "uploads"),
    }
    first = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio, json
from app.db.base import Base
from app.db.engine import engine, async_session_factory
import app.models
from app.models.submission import Submission
from app.schemas.ai_edit import AIEditRequest
from app.services import ai_edit_service as service
from app.services.ai.editor import AIEditor, EditResult

async def synthetic_edit(self, **kwargs):
    return EditResult(edited_headline="Synthetic headline", edited_body="Synthetic body.",
                      headline_case="sentence_case", ai_provider="synthetic", ai_model="test")

AIEditor.edit_submission = synthetic_edit
service.get_llm_provider = lambda settings: object()

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    ids = {}
    for status in ("queued", "running", "succeeded"):
        async with async_session_factory() as session:
            submission = Submission(Category="faculty_staff", Target_Newsletter="tdr",
                Original_Headline="Synthetic headline", Original_Body="Synthetic body.",
                Submitter_Name="Synthetic", Submitter_Email="synthetic@example.test")
            session.add(submission)
            await session.commit()
            task, _ = await service.enqueue(session, submission.Id, AIEditRequest(Newsletter_Type="tdr"))
            ids[status] = task.Id
            if status == "running":
                task.Status, task.Run_Id = "running", "abandoned-attempt"
                await session.commit()
        if status == "succeeded":
            await service.process_task(task.Id)
    await engine.dispose()
    print(json.dumps(ids))

asyncio.run(main())
""",
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    ids = json.loads(first.stdout)
    second = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio, json, sys
from app.main import app
from app.db.engine import async_session_factory, engine
from app.services import ai_edit_service as service

async def main():
    states = {}
    async with app.router.lifespan_context(app):
        async with async_session_factory() as session:
            for prior_status, task_id in json.loads(sys.argv[1]).items():
                task = await service.get_task(session, task_id)
                states[prior_status] = service.serialize_task(task).model_dump(mode="json")
    await engine.dispose()
    print(json.dumps(states))

asyncio.run(main())
""",
            json.dumps(ids),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    states = json.loads(second.stdout)
    for status in ("queued", "running"):
        assert states[status]["Task_Id"] == ids[status]
        assert states[status]["Status"] == "failed"
        assert "interrupted" in states[status]["Error_Message"]
    assert states["succeeded"]["Status"] == "succeeded"
    assert states["succeeded"]["Result"]["Edit_Version_Id"]
