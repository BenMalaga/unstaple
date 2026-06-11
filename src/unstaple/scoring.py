"""Boundary scoring: decide where one document ends and the next begins.

Signals are combined with a noisy-OR (a boundary is likely if any strong
signal fires), then multiplied by continuity dampeners (a boundary is
unlikely if page numbering or letterhead clearly continues).
"""

from __future__ import annotations

from dataclasses import dataclass

from .features import PageFeatures, header_similarity

__all__ = ["Boundary", "DEFAULT_THRESHOLD", "combine", "score_boundary", "find_boundaries", "segments"]

DEFAULT_THRESHOLD = 0.5

# signal weights
W_RESET_AFTER_COMPLETED = 0.90  # "Page 1 of N" right after "Page M of M"
W_RESET = 0.85                  # numbering drops back to 1
W_RESET_BARE = 0.70             # bare "1" after a bare higher number
W_STARTS_EXPLICIT = 0.55        # "Page 1 of N" after unnumbered pages
W_STARTS_BARE = 0.40            # bare "1" after unnumbered pages
W_PREV_COMPLETED = 0.45         # previous page was "Page M of M", next page unnumbered
W_BLANK_SEPARATOR = 0.80        # blank page(s) between the two pages
W_HEADER_SHIFT_STRONG = 0.50    # letterhead tokens nearly disjoint
W_HEADER_SHIFT_WEAK = 0.25      # letterhead tokens mostly different
W_DATE_CHANGE = 0.30            # both pages dated, no date in common

# continuity dampeners (multiply the combined score)
D_NUMBERING_CONTINUES = 0.10
D_HEADER_CONTINUES = 0.50
D_DATE_SHARED = 0.70

HEADER_SHIFT_STRONG = 0.20
HEADER_SHIFT_WEAK = 0.35
HEADER_CONTINUITY = 0.60


@dataclass(frozen=True)
class Boundary:
    """A proposed cut: the page at ``page_index`` starts a new document."""

    page_index: int
    confidence: float
    reasons: tuple[str, ...]


def combine(scores: list[float]) -> float:
    """Noisy-OR combination of independent signal scores."""
    p = 1.0
    for s in scores:
        p *= 1.0 - s
    return 1.0 - p


def score_boundary(
    prev: PageFeatures, cur: PageFeatures, blank_gap: bool = False
) -> tuple[float, tuple[str, ...]]:
    """Score the hypothesis that ``cur`` starts a new document after ``prev``.

    Returns (confidence in [0, 1], human-readable reasons).
    """
    signals: list[tuple[float, str]] = []
    dampeners: list[tuple[float, str]] = []
    reset_fired = False  # hard numbering reset overrides soft continuity below

    # --- page numbering -----------------------------------------------------
    pl, cl = prev.label, cur.label
    numbering_continues = (
        pl is not None
        and cl is not None
        and cl.number == pl.number + 1
        and (pl.total is None or cl.total is None or pl.total == cl.total)
    )
    prev_completed = pl is not None and pl.total is not None and pl.number == pl.total

    if numbering_continues:
        dampeners.append((D_NUMBERING_CONTINUES, f'page numbering continues ("{pl}" -> "{cl}")'))
    elif cl is not None and cl.number == 1:
        if pl is not None and prev_completed:
            reset_fired = True
            signals.append((W_RESET_AFTER_COMPLETED, f'page numbering reset: "{cl}" after "{pl}"'))
        elif pl is not None:
            reset_fired = True
            weight = W_RESET if (cl.explicit or pl.explicit or cl.total is not None) else W_RESET_BARE
            signals.append((weight, f'page numbering reset: "{cl}" after "{pl}"'))
        else:
            weight = W_STARTS_EXPLICIT if (cl.explicit or cl.total is not None) else W_STARTS_BARE
            signals.append((weight, f'page numbering starts ("{cl}") after unnumbered pages'))
    elif prev_completed and cl is None:
        signals.append((W_PREV_COMPLETED, f'previous page completed its numbering ("{pl}")'))

    # --- blank separator ----------------------------------------------------
    if blank_gap:
        signals.append((W_BLANK_SEPARATOR, "blank page separator"))

    # --- header / letterhead shift -------------------------------------------
    if prev.header and cur.header:
        sim = header_similarity(prev.header, cur.header)
        if sim <= HEADER_SHIFT_STRONG:
            signals.append((W_HEADER_SHIFT_STRONG, f"header shift (similarity {sim:.2f})"))
        elif sim <= HEADER_SHIFT_WEAK:
            signals.append((W_HEADER_SHIFT_WEAK, f"weak header shift (similarity {sim:.2f})"))
        elif sim >= HEADER_CONTINUITY and not reset_fired:
            # several documents from the same sender share a letterhead, so a
            # hard numbering reset overrides header continuity
            dampeners.append((D_HEADER_CONTINUES, f"header continuity (similarity {sim:.2f})"))

    # --- dates ----------------------------------------------------------------
    if prev.dates and cur.dates:
        if set(prev.dates) & set(cur.dates):
            if not reset_fired:
                dampeners.append((D_DATE_SHARED, "shared date"))
        else:
            signals.append(
                (W_DATE_CHANGE, f"date change ({prev.dates[0].isoformat()} -> {cur.dates[0].isoformat()})")
            )

    score = combine([s for s, _ in signals])
    reasons = [r for _, r in signals]
    for factor, why in dampeners:
        score *= factor
        reasons.append(f"damped: {why}")
    return score, tuple(reasons)


def find_boundaries(
    features: list[PageFeatures], threshold: float = DEFAULT_THRESHOLD
) -> list[Boundary]:
    """Scan page features and return proposed cut points above ``threshold``.

    Blank pages never start a document; they stay attached to the document
    before them (so total output pages always equal input pages) and act
    as a separator signal for the next non-blank page.
    """
    boundaries: list[Boundary] = []
    prev_visible: PageFeatures | None = None
    blank_gap = False

    for feat in features:
        if feat.blank:
            if prev_visible is not None:
                blank_gap = True
            continue
        if prev_visible is not None:
            score, reasons = score_boundary(prev_visible, feat, blank_gap)
            if score >= threshold:
                boundaries.append(Boundary(feat.index, round(score, 3), reasons))
        prev_visible = feat
        blank_gap = False
    return boundaries


def segments(num_pages: int, boundaries: list[Boundary]) -> list[tuple[int, int]]:
    """Turn cut points into (start, end-exclusive) page ranges covering all pages."""
    if num_pages <= 0:
        return []
    starts = [0] + [b.page_index for b in boundaries]
    out: list[tuple[int, int]] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else num_pages
        out.append((start, end))
    return out
