from PIL import Image
import tempfile
from pathlib import Path

import pytesseract


def _normalize_for_ocr(image_path: str) -> str:
    ext = Path(image_path).suffix.lower()
    if ext in {".jpg", ".jpeg"}:
        return image_path
    if ext == ".png":
        img = Image.open(image_path).convert("RGB")
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img.save(tmp.name, format="JPEG")
        return tmp.name
    raise ValueError("Unsupported image type")


def extract_text_from_jpg(image_path: str, tesseract_cmd: str | None = None, lang: str = "eng") -> str:
    """
    Extract text from a JPG image using Tesseract OCR.

    Args:
        image_path: Path to the JPG/JPEG file.
        tesseract_cmd: Optional full path to tesseract executable
            (useful on Windows if not in PATH).
        lang: OCR language code (default: "eng").

    Returns:
        Extracted text as a string.

    Raises:
        FileNotFoundError: If image file does not exist.
        ValueError: If file extension is not .jpg/.jpeg.
    """
    normalized = _normalize_for_ocr(image_path)

    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    with Image.open(normalized) as img:
        text = pytesseract.image_to_string(img, lang=lang)

    return text.strip()