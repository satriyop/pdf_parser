import pytest

from pdf_parser.extractor import (
    find_header_value,
    find_metric_value,
    find_site_type_and_area,
    extract_pdf_data,
)


class TestFindHeaderValue:
    def test_finds_next_word(self):
        lines = [(10.0, [(0, "Site ID"), (50, "SITE001")])]
        assert find_header_value(lines, "Site ID") == "SITE001"

    def test_returns_empty_for_missing_label(self):
        lines = [(10.0, [(0, "Other"), (50, "val")])]
        assert find_header_value(lines, "Site ID") == ""

    def test_returns_empty_if_no_next_word(self):
        lines = [(10.0, [(0, "Site ID")])]
        assert find_header_value(lines, "Site ID") == ""


class TestFindMetricValue:
    def test_finds_numeric_value(self):
        lines = [(10.0, [(0, "Jumlah Phase"), (50, "3")])]
        assert find_metric_value(lines, "Jumlah Phase") == "3"

    def test_case_insensitive(self):
        lines = [(10.0, [(0, "jumlah PHASE"), (50, "1")])]
        assert find_metric_value(lines, "Jumlah Phase") == "1"

    def test_takes_last_number(self):
        lines = [
            (10.0, [(0, "Label"), (30, "100"), (50, "200")]),
        ]
        assert find_metric_value(lines, "Label") == "200"

    def test_returns_empty_when_no_numbers(self):
        lines = [(10.0, [(0, "Label"), (50, "N/A")])]
        assert find_metric_value(lines, "Label") == ""


class TestFindSiteTypeAndArea:
    def test_outdoor_shelterless(self):
        pages = ["some text Shelterless Outdoor more text"]
        t, a = find_site_type_and_area(pages)
        assert t == "Outdoor"

    def test_indoor_shelter(self):
        pages = ["some text Shelter Indoor more text"]
        t, a = find_site_type_and_area(pages)
        assert t == "Indoor"

    def test_area_from_sqcm(self):
        pages = ["Shelterless Outdoor Area sqcm 32000"]
        t, a = find_site_type_and_area(pages)
        assert a == "3.2"

    def test_area_rounding(self):
        pages = ["Shelterless Outdoor Area sqcm 31415"]
        t, a = find_site_type_and_area(pages)
        assert a == "3.1"

    def test_defaults_when_no_match(self):
        pages = ["no relevant keywords here"]
        t, a = find_site_type_and_area(pages)
        assert t == "Outdoor"
        assert a == ""


class TestExtractPdfData:
    def test_extracts_from_real_pdf(self, sample_pdf_path):
        if not sample_pdf_path:
            pytest.skip("No PDF files found in root directory")
        data = extract_pdf_data(sample_pdf_path)
        assert isinstance(data, dict)
        assert "nama_site" in data
        assert "site_id" in data
        assert "region" in data
        # Real data should have at least something extracted
        assert data["nama_site"] or data["site_id"]
