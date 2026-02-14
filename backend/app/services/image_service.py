import os
import uuid
from pathlib import Path

from PIL import Image

from app.config import settings


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


async def save_upload(filename: str, content: bytes) -> str:
    """Save uploaded file and return the relative path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = Path(filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(settings.upload_dir, unique_name)
    with open(filepath, "wb") as f:
        f.write(content)
    return unique_name
