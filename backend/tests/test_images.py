"""Tests for submission image authorization and validation."""

from io import BytesIO

import pytest
from httpx import AsyncClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.submission import Submission
from tests.conftest import make_submission_data


def make_png_bytes(size: tuple[int, int] = (16, 16)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color=(120, 80, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture(autouse=True)
def isolate_upload_dir(tmp_path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr("app.services.image_service.settings.upload_dir", str(tmp_path))
    monkeypatch.setattr("app.api.v1.submissions.settings.upload_dir", str(tmp_path))


@pytest.mark.asyncio
class TestSubmissionImages:
    async def test_public_cannot_upload_or_read_submission_images(
        self,
        client: AsyncClient,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        upload_resp = await client.post(
            f"/api/v1/submissions/{submission_id}/image",
            files={"file": ("image.png", make_png_bytes(), "image/png")},
        )
        assert upload_resp.status_code == 403

        staff_upload_resp = await client.post(
            f"/api/v1/submissions/{submission_id}/image",
            files={"file": ("image.png", make_png_bytes(), "image/png")},
            headers=staff_headers,
        )
        assert staff_upload_resp.status_code == 200

        read_resp = await client.get(f"/api/v1/submissions/{submission_id}/image")
        assert read_resp.status_code == 403

    async def test_staff_can_upload_and_read_valid_image(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        upload_resp = await client.post(
            f"/api/v1/submissions/{submission_id}/image",
            files={"file": ("image.png", make_png_bytes(), "image/png")},
            headers=staff_headers,
        )

        assert upload_resp.status_code == 200
        body = upload_resp.json()
        assert body["Has_Image"] is True
        assert body["Image_Path"].endswith(".png")

        db.expire_all()
        submission = await db.get(Submission, submission_id)
        assert submission is not None
        assert submission.Has_Image is True
        assert submission.Image_Path == body["Image_Path"]

        read_resp = await client.get(
            f"/api/v1/submissions/{submission_id}/image",
            headers=staff_headers,
        )
        assert read_resp.status_code == 200
        assert read_resp.content.startswith(b"\x89PNG")

    async def test_oversized_image_is_rejected_before_persisting(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr("app.services.image_service.settings.image_upload_max_bytes", 16)
        monkeypatch.setattr("app.api.v1.submissions.settings.image_upload_max_bytes", 16)
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        upload_resp = await client.post(
            f"/api/v1/submissions/{submission_id}/image",
            files={"file": ("image.png", make_png_bytes(), "image/png")},
            headers=staff_headers,
        )

        assert upload_resp.status_code == 413
        submission = await db.get(Submission, submission_id)
        assert submission is not None
        assert submission.Has_Image is False
        assert submission.Image_Path is None

    async def test_corrupt_image_content_is_rejected(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
    ):
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        upload_resp = await client.post(
            f"/api/v1/submissions/{submission_id}/image",
            files={"file": ("image.png", b"not a real image", "image/png")},
            headers=staff_headers,
        )

        assert upload_resp.status_code == 422
        assert "not a real image" in upload_resp.json()["detail"]
        submission = await db.get(Submission, submission_id)
        assert submission is not None
        assert submission.Has_Image is False
        assert submission.Image_Path is None

    async def test_image_dimensions_are_limited(
        self,
        client: AsyncClient,
        db: AsyncSession,
        staff_headers: dict[str, str],
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr("app.services.image_service.settings.image_upload_max_pixels", 4)
        submission_resp = await client.post(
            "/api/v1/submissions/",
            json=make_submission_data(),
        )
        assert submission_resp.status_code == 201
        submission_id = submission_resp.json()["Id"]

        upload_resp = await client.post(
            f"/api/v1/submissions/{submission_id}/image",
            files={"file": ("image.png", make_png_bytes(size=(3, 3)), "image/png")},
            headers=staff_headers,
        )

        assert upload_resp.status_code == 422
        assert "dimensions are too large" in upload_resp.json()["detail"]
        submission = await db.get(Submission, submission_id)
        assert submission is not None
        assert submission.Has_Image is False
        assert submission.Image_Path is None


class TestGifMetadata:
    """GIFs are re-encoded so comment blocks do not survive into storage."""

    def test_comment_is_removed_and_frames_kept(self, tmp_path):
        from PIL import Image

        from app.services.image_service import _strip_exif

        path = tmp_path / "anim.gif"
        frames = [
            Image.new("RGB", (4, 4), color)
            for color in ((255, 0, 0), (0, 255, 0), (0, 0, 255))
        ]
        frames[0].save(
            path, format="GIF", save_all=True, append_images=frames[1:],
            duration=120, loop=0, comment=b"SYNTHETIC-GIF-COMMENT-7f1",
        )
        assert b"SYNTHETIC-GIF-COMMENT-7f1" in path.read_bytes()

        _strip_exif(str(path))

        assert b"SYNTHETIC-GIF-COMMENT-7f1" not in path.read_bytes()
        with Image.open(path) as cleaned:
            assert cleaned.format == "GIF"
            assert cleaned.n_frames == 3
            assert cleaned.info.get("duration") == 120

    def test_single_frame_gif_comment_is_removed(self, tmp_path):
        from PIL import Image

        from app.services.image_service import _strip_exif

        path = tmp_path / "still.gif"
        Image.new("P", (4, 4), 1).save(path, format="GIF", comment=b"SYNTHETIC-GIF-COMMENT-7f2")
        _strip_exif(str(path))
        assert b"SYNTHETIC-GIF-COMMENT-7f2" not in path.read_bytes()
