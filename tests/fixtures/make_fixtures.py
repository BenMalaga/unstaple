"""Generate synthetic 'stapled' fixture PDFs (dev-only, needs reportlab).

Each fixture concatenates several fake documents into one PDF, the way a
sheet-fed scanner with no separator logic would.

Run directly to (re)build the PDFs next to this file:

    python tests/fixtures/make_fixtures.py
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

FIXTURE_DIR = Path(__file__).parent

_LOREM = (
    "The quarterly figures referenced above are provided for information",
    "purposes only and remain subject to final reconciliation. Questions",
    "regarding this document should be directed to the office listed in",
    "the letterhead during normal business hours.",
)


def _page(c: canvas.Canvas, lines: list[str], footer: str | None = None) -> None:
    y = 740
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    if footer:
        c.drawString(72, 40, footer)
    c.showPage()


def build_basic(path: Path) -> None:
    """Three documents, each with its own 'Page X of Y' numbering and date."""
    c = canvas.Canvas(str(path), pagesize=LETTER)

    # doc 1: invoice, 2 pages, March 3 2026
    _page(c, [
        "ACME SUPPLY CO.",
        "INVOICE #4821",
        "Date: March 3, 2026",
        "Bill to: Northwind Medical Group",
        "",
        "Qty  Item                          Amount",
        "12   Nitrile gloves, box           $144.00",
        "4    Exam table paper, case        $96.00",
        "2    Sharps containers             $44.00",
    ], footer="Page 1 of 2")
    _page(c, [
        "ACME SUPPLY CO.",
        "Invoice #4821, continued",
        "",
        "6    Sterile gauze pads, case      $120.00",
        "1    Annual service plan           $880.00",
        "",
        "Total due: $1,284.00",
        "Terms: net 30 days from invoice date.",
    ], footer="Page 2 of 2")

    # doc 2: lab report, 3 pages, 2026-04-17
    _page(c, [
        "Northwind Medical Group",
        "LAB RESULTS SUMMARY",
        "Collected: 2026-04-17",
        "Patient ID: NW-3391",
        "",
        "Panel: Comprehensive metabolic",
        "Glucose ............ 92 mg/dL (normal)",
        "Creatinine ......... 0.9 mg/dL (normal)",
    ], footer="Page 1 of 3")
    _page(c, [
        "Northwind Medical Group",
        "Lab results for patient NW-3391, collected 2026-04-17",
        "",
        "Sodium ............. 140 mmol/L (normal)",
        "Potassium .......... 4.1 mmol/L (normal)",
        "Chloride ........... 102 mmol/L (normal)",
    ], footer="Page 2 of 3")
    _page(c, [
        "Northwind Medical Group",
        "Lab results for patient NW-3391, collected 2026-04-17",
        "",
        "ALT ................ 22 U/L (normal)",
        "AST ................ 25 U/L (normal)",
        "Reviewed by: T. Okafor, MD",
    ], footer="Page 3 of 3")

    # doc 3: city notice, 1 page, 05/02/2026
    _page(c, [
        "CITY OF SPRINGFIELD",
        "Parking Permit Renewal Notice",
        "Date: 05/02/2026",
        "",
        "Your residential parking permit expires on 06/30/2026.",
        "Renew online or at City Hall before the expiration date",
        "to avoid a lapse in permit coverage.",
    ], footer="Page 1 of 1")

    c.save()


def build_tricky(path: Path) -> None:
    """Doc A (numbered) + blank separator + doc B (NO page numbers, repeated
    letterhead) + doc C (numbered). The A/B boundary leans on the blank page,
    and the B/C boundary leans on the header shift and numbering start."""
    c = canvas.Canvas(str(path), pagesize=LETTER)

    # doc A: 2 pages, numbered, January 12 2026
    _page(c, [
        "RIVERSIDE DENTAL ASSOCIATES",
        "Treatment Plan Estimate",
        "Date: January 12, 2026",
        "",
        "Patient: J. Malaga",
        "D2740  Crown, porcelain/ceramic ....... $1,150.00",
        "D2950  Core buildup ................... $310.00",
    ], footer="Page 1 of 2")
    _page(c, [
        "RIVERSIDE DENTAL ASSOCIATES",
        "Treatment plan estimate, continued",
        "",
        "Estimated insurance portion ......... $730.00",
        "Estimated patient portion ........... $730.00",
        "Prepared January 12, 2026. Estimate valid for 90 days.",
    ], footer="Page 2 of 2")

    # blank separator sheet (scanner divider)
    c.showPage()

    # doc B: 3 pages, no page numbers, letterhead repeats on every page
    _page(c, [
        "Meridian Property Management",
        "445 Lakeshore Drive, Suite 200",
        "Account: 7741-RENEW",
        "",
        "RE: Annual Lease Renewal Notice",
        "February 1, 2026",
        "",
        "Dear Tenant, your lease for Unit 12B is due for renewal.",
        "The proposed terms for the coming year are enclosed.",
    ])
    _page(c, [
        "Meridian Property Management",
        "445 Lakeshore Drive, Suite 200",
        "Account: 7741-RENEW",
        "",
        "Proposed monthly rent ............... $1,640",
        "Lease term .......................... 12 months",
        "Pet addendum ........................ unchanged",
    ] + list(_LOREM))
    _page(c, [
        "Meridian Property Management",
        "445 Lakeshore Drive, Suite 200",
        "Account: 7741-RENEW",
        "",
        "Please sign and return the enclosed renewal form within",
        "30 days. Contact our office with any questions.",
        "Sincerely, Resident Services",
    ])

    # doc C: 2 pages, numbered, 03/15/2026
    _page(c, [
        "STATE BUREAU OF MOTOR VEHICLES",
        "Registration Renewal Notice",
        "Notice date: 03/15/2026",
        "",
        "Plate: 8KX-4421   VIN ending: ...90142",
        "Registration expires: 04/30/2026",
        "Renewal fee: $86.00",
    ], footer="Page 1 of 2")
    _page(c, [
        "STATE BUREAU OF MOTOR VEHICLES",
        "Registration renewal, continued",
        "",
        "Payment options: online, by mail, or in person.",
        "A late fee of $25.00 applies after the expiration date.",
    ], footer="Page 2 of 2")

    c.save()


def build_all(directory: Path = FIXTURE_DIR) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    basic = directory / "stapled_basic.pdf"
    tricky = directory / "stapled_tricky.pdf"
    build_basic(basic)
    build_tricky(tricky)
    return {"basic": basic, "tricky": tricky}


if __name__ == "__main__":
    for name, p in build_all().items():
        print(f"built {name}: {p}")
