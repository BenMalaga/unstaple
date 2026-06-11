from unstaple.features import page_features
from unstaple.naming import infer_stem, slugify, title_for, uniquify


class TestSlugify:
    def test_basic(self):
        assert slugify("ACME Supply Co.") == "acme-supply-co"

    def test_symbols(self):
        assert slugify("INVOICE #4821") == "invoice-4821"

    def test_truncates_on_word_boundary(self):
        slug = slugify("alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo")
        assert len(slug) <= 60
        assert not slug.endswith("-")
        assert slug.split("-")[-1] in slug  # still whole words


class TestTitle:
    def test_skips_page_label_and_date_lines(self):
        lines = ("Page 1 of 2", "03/05/2026", "Quarterly Safety Review", "body text")
        assert title_for(lines) == "Quarterly Safety Review"

    def test_appends_following_caps_title(self):
        lines = ("Northwind Medical Group", "LAB RESULTS SUMMARY", "Collected: 2026-04-17")
        assert title_for(lines) == "Northwind Medical Group LAB RESULTS SUMMARY"

    def test_does_not_append_lowercase_line(self):
        lines = ("CITY OF SPRINGFIELD", "Parking Permit Renewal Notice")
        assert title_for(lines) == "CITY OF SPRINGFIELD"

    def test_no_usable_lines(self):
        assert title_for(("Page 1 of 2", "1/2/2026", "")) is None


class TestStem:
    def test_date_plus_title(self):
        feat = page_features(0, "ACME SUPPLY CO.\nINVOICE #4821\nDate: March 3, 2026")
        assert infer_stem(feat, 1) == "2026-03-03-acme-supply-co-invoice-4821"

    def test_title_only(self):
        feat = page_features(0, "Meridian Property Management\nno dates here")
        assert infer_stem(feat, 1) == "meridian-property-management"

    def test_fallback_ordinal(self):
        feat = page_features(0, "x1 y2\n9 of 9")
        assert infer_stem(feat, 3) == "document-03"


class TestUniquify:
    def test_no_dupes(self):
        assert uniquify(["a", "b"]) == ["a", "b"]

    def test_dupes_get_suffixes(self):
        assert uniquify(["a", "a", "a", "b"]) == ["a", "a-2", "a-3", "b"]
