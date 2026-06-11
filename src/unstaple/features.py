"""Per-page feature extraction from a PDF text layer.

Everything in this module is a pure function of the extracted page text,
so the boundary heuristics stay deterministic and unit-testable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

__all__ = [
    "PageLabel",
    "PageFeatures",
    "extract_page_label",
    "extract_dates",
    "header_fingerprint",
    "header_similarity",
    "is_blank_text",
    "looks_like_page_label_line",
    "page_features",
]

# --------------------------------------------------------------------------
# page-number labels
# --------------------------------------------------------------------------

_PAGE_OF_RE = re.compile(r"\bpage\s+(\d{1,4})\s*(?:of|/)\s*(\d{1,4})\b", re.IGNORECASE)
_PAGE_N_RE = re.compile(r"\bpage\s+(\d{1,4})\b", re.IGNORECASE)
_N_OF_M_RE = re.compile(r"^\s*(\d{1,4})\s*(?:of|/)\s*(\d{1,4})\s*$", re.IGNORECASE)
_DASH_N_RE = re.compile(r"^\s*-+\s*(\d{1,3})\s*-+\s*$")
_BARE_N_RE = re.compile(r"^\s*(\d{1,3})\s*$")


@dataclass(frozen=True)
class PageLabel:
    """A page number printed on the page, e.g. 'Page 2 of 5' or a bare '2'."""

    number: int
    total: int | None = None
    explicit: bool = False  # True when the word "page" appears

    def __str__(self) -> str:
        prefix = "Page " if self.explicit else ""
        if self.total is not None:
            return f"{prefix}{self.number} of {self.total}"
        return f"{prefix}{self.number}"


def _edge_lines(lines: tuple[str, ...], k: int = 2) -> list[str]:
    """First and last k non-blank lines: where printed page numbers live."""
    nonblank = [ln for ln in lines if ln.strip()]
    if len(nonblank) <= 2 * k:
        return nonblank
    return nonblank[:k] + nonblank[-k:]


def extract_page_label(lines: tuple[str, ...]) -> PageLabel | None:
    """Parse a printed page number from page text, most reliable form first."""
    text = "\n".join(lines)
    m = _PAGE_OF_RE.search(text)
    if m:
        number, total = int(m.group(1)), int(m.group(2))
        if 1 <= number <= total:
            return PageLabel(number, total, explicit=True)
        return None  # a garbled "Page X of Y" marking is not worth guessing about

    edges = _edge_lines(lines)
    for ln in edges:
        m = _N_OF_M_RE.match(ln)
        if m:
            number, total = int(m.group(1)), int(m.group(2))
            if 1 <= number <= total:
                return PageLabel(number, total, explicit=False)
    for ln in edges:
        m = _PAGE_N_RE.search(ln)
        if m and int(m.group(1)) >= 1:
            return PageLabel(int(m.group(1)), explicit=True)
    for ln in edges:
        m = _DASH_N_RE.match(ln)
        if m and int(m.group(1)) >= 1:
            return PageLabel(int(m.group(1)))
    for ln in edges:
        m = _BARE_N_RE.match(ln)
        if m and int(m.group(1)) >= 1:
            return PageLabel(int(m.group(1)))
    return None


def looks_like_page_label_line(line: str) -> bool:
    """True for lines that are only a page-number marking."""
    return bool(
        _N_OF_M_RE.match(line)
        or _DASH_N_RE.match(line)
        or _BARE_N_RE.match(line)
        or re.match(r"^\s*page\s+\d{1,4}(\s*(?:of|/)\s*\d{1,4})?\s*$", line, re.IGNORECASE)
    )


# --------------------------------------------------------------------------
# dates
# --------------------------------------------------------------------------

_MON = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)
_ISO_RE = re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")
_SLASH_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
_MDY_RE = re.compile(rf"\b{_MON}\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.IGNORECASE)
_DMY_RE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MON}\.?,?\s+(\d{{4}})\b", re.IGNORECASE)

_MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _month_num(name: str) -> int:
    return _MONTH_NUM[name.lower()[:3]]


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def extract_dates(text: str) -> tuple[date, ...]:
    """All dates found in the text, in order of appearance, de-duplicated."""
    found: list[tuple[int, date]] = []
    for m in _ISO_RE.finditer(text):
        d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            found.append((m.start(), d))
    for m in _SLASH_RE.finditer(text):
        mo, dy, yr = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if mo > 12 and dy <= 12:  # tolerate DD/MM/YYYY
            mo, dy = dy, mo
        d = _safe_date(yr, mo, dy)
        if d:
            found.append((m.start(), d))
    for m in _MDY_RE.finditer(text):
        d = _safe_date(int(m.group(3)), _month_num(m.group(1)), int(m.group(2)))
        if d:
            found.append((m.start(), d))
    for m in _DMY_RE.finditer(text):
        d = _safe_date(int(m.group(3)), _month_num(m.group(2)), int(m.group(1)))
        if d:
            found.append((m.start(), d))

    found.sort(key=lambda pair: pair[0])
    out: list[date] = []
    for _, d in found:
        if d not in out:
            out.append(d)
    return tuple(out)


# --------------------------------------------------------------------------
# header fingerprint
# --------------------------------------------------------------------------

def header_fingerprint(lines: tuple[str, ...], k: int = 3) -> frozenset[str]:
    """Token set of the first k non-blank, non-page-label lines (letterhead area).

    Digits are dropped so page counters and reference numbers inside a
    repeated letterhead do not break per-document continuity.
    """
    head = [ln for ln in lines if ln.strip() and not looks_like_page_label_line(ln)][:k]
    tokens: set[str] = set()
    for ln in head:
        cleaned = re.sub(r"[^a-z ]+", " ", ln.lower())
        tokens.update(tok for tok in cleaned.split() if len(tok) > 1)
    return frozenset(tokens)


def header_similarity(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity of two header fingerprints."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------

def is_blank_text(text: str) -> bool:
    """True when the page has no usable text layer content."""
    return sum(ch.isalnum() for ch in text) < 3


@dataclass(frozen=True)
class PageFeatures:
    """Deterministic signals extracted from one page."""

    index: int  # zero-based position in the source PDF
    lines: tuple[str, ...]
    label: PageLabel | None
    dates: tuple[date, ...]
    header: frozenset[str]
    blank: bool


def page_features(index: int, text: str) -> PageFeatures:
    """Extract all boundary signals from one page of text."""
    lines = tuple(text.splitlines())
    blank = is_blank_text(text)
    if blank:
        return PageFeatures(index, lines, None, (), frozenset(), True)
    return PageFeatures(
        index=index,
        lines=lines,
        label=extract_page_label(lines),
        dates=extract_dates(text),
        header=header_fingerprint(lines),
        blank=False,
    )
