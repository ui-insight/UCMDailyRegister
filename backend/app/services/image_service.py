import logging
import os
import uuid
from pathlib import Path

from PIL import Image

from app.config import settings


logger = logging.getLogger(__name__)


class ImageProcessingError(Exception):
    """Raised when an uploaded image cannot be processed safely (e.g., EXIF stripping failed)."""


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_image(filename: str, file_size: int) -> str | None:
    """Return an error message if invalid, None if valid."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"File type '{ext}' not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size > MAX_FILE_SIZE:
        return f"File too large ({file_size // 1024 // 1024}MB). Max is 10MB."
    return None


def check_image_dimensions(filepath: str) -> tuple[int, int]:
    """Return (width, height) of an image file."""
    with Image.open(filepath) as img:
        return img.size


def _strip_exif(filepath: str) -> None:
    """Remove EXIF metadata (GPS, camera info, etc.) from an image file.

    Raises whatever PIL raises if the file can't be decoded or re-saved; the
    caller is responsible for cleanup and user-facing error handling.
    """
    with Image.open(filepath) as img:
        if img.format == "GIF":
            return
        cleaned = Image.new(img.mode, img.size)
        cleaned.putdata(list(img.getdata()))
        cleaned.save(filepath, format=img.format)


async def save_upload(filename: str, content: bytes) -> str:
    """Save uploaded file, strip EXIF metadata, and return the relative path.

    Fails closed: if EXIF stripping fails (corrupt file, unsupported format,
    or a file whose extension lies about its content), the saved file is
    deleted and ImageProcessingError is raised. We would rather reject an
    upload than silently store an image with metadata intact.
    """
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(settings.upload_dir, unique_name)
    with open(filepath, "wb") as f:
        f.write(content)
    try:
        _strip_exif(filepath)
    except Exception as exc:
        logger.warning(
            "Failed to strip EXIF from upload %s (stored as %s): %s",
            filename,
            unique_name,
            exc,
            exc_info=True,
        )
        try:
            os.remove(filepath)
        except OSError:
            logger.warning("Failed to clean up unprocessable upload %s", filepath)
        raise ImageProcessingError(
            "Unable to process image. The file may be corrupt, not a real image, "
            "or in an unsupported format."
        ) from exc
    return unique_name
