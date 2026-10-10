"""Convert uploaded images in memory, with orientation and transparency handling."""

import io
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

FORMATS = {
    "PNG": ("png", "image/png"),
    "JPEG": ("jpg", "image/jpeg"),
    "WEBP": ("webp", "image/webp"),
    "TIFF": ("tiff", "image/tiff"),
}


def convert_image(
    data: bytes, output_format="PNG", size=None, keep_aspect=True, quality=90
):
    if output_format not in FORMATS:
        raise ValueError("Choose PNG, JPEG, WEBP, or TIFF.")
    if not data or len(data) > 10 * 1024 * 1024:
        raise ValueError("Choose an image up to 10 MB.")
    if not isinstance(quality, int) or not 1 <= quality <= 100:
        raise ValueError("Quality must be between 1 and 100.")
    if size and (
        len(size) != 2
        or any(
            isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 4096
            for v in size
        )
    ):
        raise ValueError("Width and height must be between 1 and 4096.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as original:
                if original.width * original.height > 25_000_000:
                    raise ValueError("Choose an image with at most 25 million pixels.")
                image = ImageOps.exif_transpose(original).convert("RGBA")
        if size:
            image = (
                ImageOps.contain(image, size, Image.Resampling.LANCZOS)
                if keep_aspect
                else image.resize(size, Image.Resampling.LANCZOS)
            )
        if output_format == "JPEG":
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        image.info.clear()
        buffer = io.BytesIO()
        options = {"quality": quality} if output_format in ("JPEG", "WEBP") else {}
        image.save(buffer, format=output_format, **options)
        return buffer.getvalue(), image.size
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValueError("This file could not be read as a supported image.") from error


def output_name(filename: str, output_format: str, index: int) -> str:
    stem = Path(filename).stem.replace("\\", "_").replace("/", "_")[:80] or "image"
    return f"{index:02d}-{stem}.{FORMATS[output_format][0]}"
