"""Retired settings in an older .env file don't stop the app from starting."""

from app.config import Settings


def test_env_file_with_retired_job_listing_cap_still_loads(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("JOB_POSTINGS_MAX_LISTINGS=150\n", encoding="utf-8")
    Settings(_env_file=env_file)
