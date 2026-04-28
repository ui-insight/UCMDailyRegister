import logging
import os
import uuid
from pathlib import Path

from PIL import Image
from fastapi import UploadFile

from app.config import settings


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Raised when an uploaded image cannot be processed safely (e.g., EXIF stripping failed)."""


class ImageTooLargeError(ImageProcessingError):
    """Raised when an uploaded image exceeds the configured byte limit."""


ALLOWED_IMAGE_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".gif": "GIF",
    ".webp": "WEBP",
}
UPLOAD_CHUNK_SIZE = 1024 * 1024


def validate_image_filename(filename: str) -> str | None:
    """Return an error message if invalid, None if valid."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_FORMATS:
        return f"File type '{ext}' not allowed. Use: {', '.join(ALLOWED_IMAGE_FORMATS)}"
    return None


def check_image_dimensions(filepath: str) -> tuple[int, int]:
    """Return (width, height) of an image file."""
    with Image.open(filepath) as img:
        return img.size


def _verify_image_file(filepath: str, filename: str) -> tuple[str, tuple[int, int]]:
    """Validate actual image format and dimensions, returning format and size."""
    ext = Path(filename).suffix.lower()
    expected_format = ALLOWED_IMAGE_FORMATS[ext]

    try:
        with Image.open(filepath) as img:
            actual_format = img.format
            width, height = img.size
            img.verify()
    except Exception as exc:
        raise ImageProcessingError(
            "Unable to process image. The file may be corrupt or not a real image."
        ) from exc

    if actual_format != expected_format:
        raise ImageProcessingError(
            f"Image content is {actual_format or 'unknown'}, but the filename uses '{ext}'."
        )

    if width <= 0 or height <= 0:
        raise ImageProcessingError("Image dimensions are invalid.")

    pixel_count = width * height
    if pixel_count > settings.image_upload_max_pixels:
        raise ImageProcessingError(
            f"Image dimensions are too large ({width}x{height})."
        )

    return actual_format, (width, height)


def _strip_exif(filepath: str) -> None:
    """Remove EXIF metadata (GPS, camera info, etc.) from an image file.

    Raises whatever PIL raises if the file can't be decoded or re-saved; the
    caller is responsible for cleanup and user-facing error handling.
    """
    with Image.open(filepath) as img:
        if img.format == "GIF":
            return
        cleaned = img.copy()
        cleaned.save(filepath, format=img.format)


async def save_upload_file(file: UploadFile, filename: str) -> str:
    """Stream an uploaded image to disk, validate real content, strip EXIF, and return path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    final_path = os.path.join(settings.upload_dir, unique_name)
    temp_path = f"{final_path}.part"

    total_size = 0
    try:
        with open(temp_path, "wb") as f:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > settings.image_upload_max_bytes:
                    raise ImageTooLargeError(
                        f"File too large. Max is {settings.image_upload_max_bytes // 1024 // 1024}MB."
                    )
                f.write(chunk)

        _verify_image_file(temp_path, filename)
        os.replace(temp_path, final_path)
        _strip_exif(final_path)
    except ImageProcessingError:
        for path in (temp_path, final_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                logger.warning("Failed to clean up rejected upload %s", path)
        raise
    except Exception as exc:
        for path in (temp_path, final_path):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                logger.warning("Failed to clean up unprocessable upload %s", path)
        raise ImageProcessingError(
            "Unable to process image. The file may be corrupt, not a real image, "
            "or in an unsupported format."
        ) from exc

    return unique_name
