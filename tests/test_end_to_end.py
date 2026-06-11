"""End-to-end: generate stapled fixtures, split them, verify boundaries and names."""

from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfReader

from unstaple.cli import main


def run_split(pdf: Path, out_dir: Path, capsys) -> tuple[int, str, list[Path]]:
    rc = main([str(pdf), "--out-dir", str(out_dir)])
    out = capsys.readouterr().out
    files = sorted(out_dir.glob("*.pdf")) if out_dir.is_dir() else []
    return rc, out, files


class TestBasicFixture:
    """3 docs, each with independent 'Page X of Y' numbering: 2 + 3 + 1 pages."""

    @pytest.fixture(autouse=True)
    def _split(self, fixture_pdfs, tmp_path, capsys):
        self.rc, self.out, self.files = run_split(
            fixture_pdfs["basic"], tmp_path / "out", capsys
        )

    def test_exit_code(self):
        assert self.rc == 0

    def test_exactly_three_documents(self):
        assert len(self.files) == 3

    def test_boundaries_are_correct(self):
        page_counts = sorted(len(PdfReader(str(f)).pages) for f in self.files)
        assert page_counts == [1, 2, 3]

    def test_names_are_sensible(self):
        names = sorted(f.name for f in self.files)
        assert names == [
            "2026-03-03-acme-supply-co-invoice-4821.pdf",
            "2026-04-17-northwind-medical-group-lab-results-summary.pdf",
            "2026-05-02-city-of-springfield.pdf",
        ]

    def test_each_split_starts_with_its_own_letterhead(self):
        by_name = {f.name: f for f in self.files}
        first_page_text = {
            name: PdfReader(str(f)).pages[0].extract_text()
            for name, f in by_name.items()
        }
        assert "ACME SUPPLY" in first_page_text["2026-03-03-acme-supply-co-invoice-4821.pdf"]
        assert "LAB RESULTS" in first_page_text[
            "2026-04-17-northwind-medical-group-lab-results-summary.pdf"
        ]
        assert "SPRINGFIELD" in first_page_text["2026-05-02-city-of-springfield.pdf"]

    def test_reported_cut_reasons_mention_numbering_reset(self):
        assert "page numbering reset" in self.out


class TestTrickyFixture:
    """Doc A (numbered) + blank sheet + doc B (no page numbers) + doc C.

    The B boundary must come from the blank separator and header shift;
    the C boundary from numbering starting at 1 plus header shift.
    """

    @pytest.fixture(autouse=True)
    def _split(self, fixture_pdfs, tmp_path, capsys):
        self.rc, self.out, self.files = run_split(
            fixture_pdfs["tricky"], tmp_path / "out", capsys
        )

    def test_exactly_three_documents(self):
        assert self.rc == 0
        assert len(self.files) == 3

    def test_boundaries_blank_page_stays_with_previous_doc(self):
        # input is 8 pages: A(2) + blank(1) + B(3) + C(2)
        counts = {f.name: len(PdfReader(str(f)).pages) for f in self.files}
        assert counts == {
            "2026-01-12-riverside-dental-associates.pdf": 3,  # 2 + trailing blank
            "2026-02-01-meridian-property-management.pdf": 3,
            "2026-03-15-state-bureau-of-motor-vehicles.pdf": 2,
        }

    def test_unnumbered_doc_not_oversplit(self):
        # doc B has 3 pages and no page numbers; header continuity must hold it together
        meridian = [f for f in self.files if "meridian" in f.name]
        assert len(meridian) == 1

    def test_cut_reasons(self):
        assert "blank page separator" in self.out
        assert "header shift" in self.out


class TestDryRun:
    def test_dry_run_writes_nothing(self, fixture_pdfs, tmp_path, capsys):
        out_dir = tmp_path / "out"
        rc = main([str(fixture_pdfs["basic"]), "--dry-run", "--out-dir", str(out_dir)])
        out = capsys.readouterr().out
        assert rc == 0
        assert not out_dir.exists()
        assert "dry run: nothing written" in out
        assert "confidence" in out


class TestErrorPaths:
    def test_missing_file(self, tmp_path, capsys):
        rc = main([str(tmp_path / "nope.pdf")])
        assert rc == 2
        assert "no such file" in capsys.readouterr().err

    def test_image_only_pdf_rejected(self, tmp_path, capsys):
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas

        path = tmp_path / "image_only.pdf"
        c = canvas.Canvas(str(path), pagesize=LETTER)
        c.rect(100, 100, 200, 200, fill=1)  # ink, but no text layer
        c.showPage()
        c.save()

        rc = main([str(path)])
        assert rc == 2
        err = capsys.readouterr().err
        assert "no extractable text" in err and "OCR" in err

    def test_single_document_not_split(self, tmp_path, capsys):
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas

        path = tmp_path / "single.pdf"
        c = canvas.Canvas(str(path), pagesize=LETTER)
        for n in (1, 2):
            c.drawString(72, 700, "Same Letterhead Co.")
            c.drawString(72, 680, f"continuing prose, part {n}")
            c.drawString(72, 40, f"Page {n} of 2")
            c.showPage()
        c.save()

        out_dir = tmp_path / "out"
        rc = main([str(path), "--out-dir", str(out_dir)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "nothing to unstaple" in out
        assert not out_dir.exists()
