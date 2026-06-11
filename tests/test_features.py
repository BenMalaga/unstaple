from datetime import date

from unstaple.features import (
    PageLabel,
    extract_dates,
    extract_page_label,
    header_fingerprint,
    header_similarity,
    is_blank_text,
    page_features,
)


def label(text: str) -> PageLabel | None:
    return extract_page_label(tuple(text.splitlines()))


class TestPageLabel:
    def test_page_x_of_y(self):
        assert label("hello\nworld\nPage 3 of 10") == PageLabel(3, 10, explicit=True)

    def test_page_slash_total(self):
        assert label("body\nPage 2/4") == PageLabel(2, 4, explicit=True)

    def test_bare_n_of_m_footer(self):
        assert label("body text\nmore body\n2 of 7") == PageLabel(2, 7, explicit=False)

    def test_page_n_no_total(self):
        assert label("text\nPage 5") == PageLabel(5, explicit=True)

    def test_dash_wrapped_number(self):
        assert label("text\n- 4 -") == PageLabel(4)

    def test_bare_trailing_number(self):
        assert label("some paragraph\n12") == PageLabel(12)

    def test_no_label(self):
        assert label("Dear sir,\nthank you for your letter.") is None

    def test_number_larger_than_total_rejected(self):
        assert label("Page 9 of 2") is None

    def test_year_not_mistaken_for_bare_page_number(self):
        # bare-number form only accepts up to 3 digits
        assert label("annual report\n2026") is None

    def test_label_in_middle_of_body_only_for_explicit_form(self):
        # "Page X of Y" is trusted anywhere; bare numbers only at page edges
        assert label("a\nb\nThis form (see Page 2 of 6) ...\nc\nd\ne") == PageLabel(2, 6, explicit=True)


class TestDates:
    def test_iso(self):
        assert extract_dates("Collected: 2026-04-17") == (date(2026, 4, 17),)

    def test_us_slash(self):
        assert extract_dates("Date: 05/02/2026") == (date(2026, 5, 2),)

    def test_dd_mm_slash_fallback(self):
        assert extract_dates("sent 23/04/2026") == (date(2026, 4, 23),)

    def test_month_name(self):
        assert extract_dates("Date: March 3, 2026") == (date(2026, 3, 3),)

    def test_abbreviated_month(self):
        assert extract_dates("Sep 9, 2025") == (date(2025, 9, 9),)

    def test_day_first(self):
        assert extract_dates("on 12 January 2026 we met") == (date(2026, 1, 12),)

    def test_invalid_date_skipped(self):
        assert extract_dates("02/30/2026") == ()

    def test_order_and_dedup(self):
        text = "From 2026-01-05 to 2026-02-06, signed January 5, 2026"
        assert extract_dates(text) == (date(2026, 1, 5), date(2026, 2, 6))


class TestHeaders:
    def test_identical_headers(self):
        a = header_fingerprint(("Acme Supply Co.", "Invoice dept."))
        b = header_fingerprint(("Acme Supply Co.", "Invoice dept."))
        assert header_similarity(a, b) == 1.0

    def test_disjoint_headers(self):
        a = header_fingerprint(("Acme Supply Co.",))
        b = header_fingerprint(("City of Springfield",))
        assert header_similarity(a, b) == 0.0

    def test_digits_ignored(self):
        a = header_fingerprint(("Meridian Property 1",))
        b = header_fingerprint(("Meridian Property 2",))
        assert header_similarity(a, b) == 1.0

    def test_blank_lines_skipped(self):
        a = header_fingerprint(("", "  ", "Acme Supply"))
        assert "acme" in a and "supply" in a


class TestBlankAndAssembly:
    def test_blank_text(self):
        assert is_blank_text("")
        assert is_blank_text("  \n . \n")
        assert not is_blank_text("Dear tenant")

    def test_page_features_blank(self):
        feat = page_features(3, "")
        assert feat.blank and feat.label is None and feat.dates == ()

    def test_page_features_full(self):
        feat = page_features(0, "ACME CO.\nInvoice\nDate: 2026-04-17\nPage 1 of 2")
        assert not feat.blank
        assert feat.label == PageLabel(1, 2, explicit=True)
        assert feat.dates == (date(2026, 4, 17),)
        assert "acme" in feat.header
