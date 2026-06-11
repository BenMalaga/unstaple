from unstaple.features import page_features
from unstaple.scoring import (
    DEFAULT_THRESHOLD,
    combine,
    find_boundaries,
    score_boundary,
    segments,
)


def feats(*texts: str):
    return [page_features(i, t) for i, t in enumerate(texts)]


class TestCombine:
    def test_empty(self):
        assert combine([]) == 0.0

    def test_single(self):
        assert combine([0.7]) == 0.7

    def test_noisy_or(self):
        assert abs(combine([0.5, 0.5]) - 0.75) < 1e-9

    def test_never_exceeds_one(self):
        assert combine([0.9, 0.9, 0.9]) <= 1.0


class TestScoreBoundary:
    def test_numbering_reset_after_completed_is_strong(self):
        prev, cur = feats("Letter one\nPage 2 of 2", "Letter two\nPage 1 of 3")
        score, reasons = score_boundary(prev, cur)
        assert score >= 0.9
        assert any("reset" in r for r in reasons)

    def test_numbering_continuation_suppresses_header_shift(self):
        # totally different headers, but Page 1 -> Page 2 of the same count
        prev, cur = feats(
            "GRAND TITLE PAGE\nof some report\nPage 1 of 3",
            "completely different body text here\nno common words at all\nPage 2 of 3",
        )
        score, reasons = score_boundary(prev, cur)
        assert score < DEFAULT_THRESHOLD
        assert any("continues" in r for r in reasons)

    def test_header_shift_alone_can_cut(self):
        prev, cur = feats(
            "Meridian Property Management\nresident services desk",
            "STATE BUREAU OF MOTOR VEHICLES\nregistration division",
        )
        score, reasons = score_boundary(prev, cur)
        assert any("header shift" in r for r in reasons)
        assert score >= DEFAULT_THRESHOLD

    def test_header_continuity_dampens(self):
        prev, cur = feats(
            "Meridian Property Management\nSuite 200",
            "Meridian Property Management\nSuite 200\nnew paragraph about rent",
        )
        score, _ = score_boundary(prev, cur)
        assert score < DEFAULT_THRESHOLD

    def test_date_change_is_weak_alone(self):
        prev, cur = feats(
            "alpha beta gamma delta on 2026-01-05",
            "alpha beta gamma delta on 2026-03-09",
        )
        score, reasons = score_boundary(prev, cur)
        assert any("date change" in r for r in reasons)
        assert score < DEFAULT_THRESHOLD  # a date change alone should not cut

    def test_blank_gap_signal(self):
        prev, cur = feats("Sincerely,\nResident Services", "NEW DOCUMENT TITLE\nintro line")
        score, reasons = score_boundary(prev, cur, blank_gap=True)
        assert any("blank" in r for r in reasons)
        assert score >= DEFAULT_THRESHOLD


class TestFindBoundaries:
    def test_no_signals_no_cuts(self):
        fs = feats(
            "Meridian Property Management\nintro",
            "Meridian Property Management\nmiddle",
            "Meridian Property Management\nend",
        )
        assert find_boundaries(fs) == []

    def test_reset_cut_found(self):
        fs = feats(
            "ACME CO.\nInvoice\nPage 1 of 2",
            "ACME CO.\ncontinued\nPage 2 of 2",
            "CITY OF SPRINGFIELD\nNotice\nPage 1 of 1",
        )
        cuts = find_boundaries(fs)
        assert [b.page_index for b in cuts] == [2]
        assert cuts[0].confidence >= 0.9

    def test_blank_page_never_starts_a_document(self):
        fs = feats(
            "DOC ONE\nbody\nPage 1 of 1",
            "",
            "DOC TWO\nopening words\ntotally different header",
        )
        cuts = find_boundaries(fs)
        assert [b.page_index for b in cuts] == [2]

    def test_leading_blank_page_ignored(self):
        fs = feats("", "ONLY DOC\nbody text here")
        assert find_boundaries(fs) == []

    def test_threshold_is_respected(self):
        fs = feats(
            "Meridian Property Management\non 2026-01-05",
            "Meridian Property Management\non 2026-03-09",
        )
        assert find_boundaries(fs, threshold=0.9) == []
        assert len(find_boundaries(fs, threshold=0.01)) == 1


class TestSegments:
    def test_no_boundaries(self):
        assert segments(4, []) == [(0, 4)]

    def test_with_boundaries(self):
        cuts = find_boundaries(
            feats(
                "A\nx\nPage 1 of 1",
                "B HEADER WORDS\nstart\nPage 1 of 2",
                "B HEADER WORDS\nend\nPage 2 of 2",
            )
        )
        assert segments(3, cuts) == [(0, 1), (1, 3)]

    def test_empty_pdf(self):
        assert segments(0, []) == []
