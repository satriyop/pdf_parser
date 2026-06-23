import os
import subprocess
from unittest.mock import patch, MagicMock

import pytest

from pdf_parser.gps import extract_gps, _ocr_image, _extract_from_images, GPS_PATTERN


class TestGpsPattern:
    def test_matches_valid_coords(self):
        text = "lat = -7.80272834\nlng = 114.12681752"
        m = GPS_PATTERN.search(text)
        assert m is not None
        assert m.group(1) == "-7.80272834"
        assert m.group(2) == "114.12681752"

    def test_matches_with_typo_1ng(self):
        text = "lat = -7.80272834\n1ng = 114.12681752"
        m = GPS_PATTERN.search(text)
        assert m is not None

    def test_rejects_missing_lat(self):
        text = "lng = 114.12681752"
        m = GPS_PATTERN.search(text)
        assert m is None

    def test_rejects_short_lng_less_than_100(self):
        text = "lat = -7.8\n1ng = 14.1"
        m = GPS_PATTERN.search(text)
        assert m is not None


class TestOcrImage:
    def test_returns_text_when_tesseract_succeeds(self, tmp_path):
        img = tmp_path / "test.jpg"
        img.write_text("fake jpg")

        def mock_tesseract(args, **kwargs):
            outpath = args[-1]
            with open(outpath + ".txt", "w") as f:
                f.write("lat = -7.8\nlng = 114.1")

        with patch("subprocess.run", side_effect=mock_tesseract):
            result = _ocr_image(str(img))
            assert result == "lat = -7.8\nlng = 114.1"

    def test_returns_empty_when_ocr_fails(self, tmp_path):
        img = tmp_path / "test.jpg"
        img.write_text("fake jpg")

        with patch("subprocess.run"):
            result = _ocr_image(str(img))
            assert result == ""


class TestExtractFromImages:
    def test_filters_small_images(self, tmp_path):
        big = tmp_path / "big.jpg"
        big.write_bytes(b"x" * 100000)
        small = tmp_path / "small.jpg"
        small.write_bytes(b"x" * 10000)

        with patch("pdf_parser.gps._ocr_image", return_value=""):
            lat, lng = _extract_from_images(str(tmp_path))
        assert lat is None

    def test_picks_best_candidate_near_115(self, tmp_path):
        img1 = tmp_path / "img1.jpg"
        img1.write_bytes(b"x" * 100000)
        img2 = tmp_path / "img2.jpg"
        img2.write_bytes(b"x" * 100000)

        def mock_ocr(path, verbose=False):
            if "img1" in path:
                return "lat=-7.8\nlng=144.12683"
            return "lat=-7.8\nlng=114.12681"

        with patch("pdf_parser.gps._ocr_image", side_effect=mock_ocr):
            lat, lng = _extract_from_images(str(tmp_path))
            assert lng == "114.12681"

    def test_returns_none_when_no_valid_gps(self, tmp_path):
        img = tmp_path / "img.jpg"
        img.write_bytes(b"x" * 100000)

        with patch("pdf_parser.gps._ocr_image", return_value="no gps data"):
            lat, lng = _extract_from_images(str(tmp_path))
            assert lat is None


class TestExtractGps:
    def test_returns_coords_when_found(self, tmp_path):
        img = tmp_path / "img-004.jpg"
        img.write_bytes(b"x" * 100000)

        with (
            patch("subprocess.run") as mock_pdfimages,
            patch("os.listdir", return_value=[]),
            patch("pdf_parser.gps._extract_from_images", return_value=("-7.8", "114.1")),
        ):
            result = extract_gps("dummy.pdf")
            assert "lat= -7.8" in result
            assert "lng= 114.1" in result

    def test_returns_empty_string_on_failure(self, tmp_path):
        with (
            patch("subprocess.run") as mock_pdfimages,
            patch("os.listdir", return_value=[]),
        ):
            result = extract_gps("dummy.pdf")
            assert result == ""
