from pathlib import Path
from typing import List

import fitz  # PyMuPDF


def pdf_to_jpgs(pdf_path: str | Path, output_dir: str | Path, dpi: int = 200) -> List[str]:
    """
    Convert each page of a PDF to a JPG image.

    Args:
        pdf_path: Path to the input PDF file.
        output_dir: Directory where JPG files will be written.
        dpi: Render resolution. Higher DPI = larger, clearer images.

    Returns:
        A list of output JPG file paths (as strings), one per page.
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    saved_files: List[str] = []

    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            filename = f"{pdf_path.stem}_page_{i:03d}.jpg"
            out_path = output_dir / filename
            pix.save(str(out_path))
            saved_files.append(str(out_path))

    return saved_files