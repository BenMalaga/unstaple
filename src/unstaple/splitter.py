"""Read a stapled PDF, extract per-page features, and write split documents."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .features import PageFeatures, page_features

__all__ = ["NoTextLayerError", "load_features", "write_segment"]


class NoTextLayerError(RuntimeError):
    """Raised when no page in the PDF has extractable text."""


def load_features(pdf_path: Path) -> tuple[PdfReader, list[PageFeatures]]:
    """Open a PDF and extract boundary signals from every page."""
    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:  # pragma: no cover - depends on input
            raise RuntimeError(f"{pdf_path}: encrypted PDF; decrypt it first") from exc

    features = []
    for index, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:  # damaged page content stream
            text = ""
        features.append(page_features(index, text))

    if features and all(f.blank for f in features):
        raise NoTextLayerError(
            f"{pdf_path}: no extractable text on any page. unstaple v0.1 needs "
            "a text layer (image-only scans are on the roadmap). Run the PDF "
            "through OCR first, e.g. `ocrmypdf in.pdf out.pdf`."
        )
    return reader, features


def write_segment(reader: PdfReader, start: int, end: int, out_path: Path) -> None:
    """Write pages [start, end) of reader to out_path."""
    writer = PdfWriter()
    for i in range(start, end):
        writer.add_page(reader.pages[i])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as fh:
        writer.write(fh)
