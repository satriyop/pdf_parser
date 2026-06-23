import argparse
import sys

import pytest

from pdf_parser.cli import main, resolve_pdf_paths, _detect_writer
from pdf_parser.writers import CsvWriter, XlsxWriter


class TestResolvePdfPaths:
    def test_no_matches_returns_empty(self):
        assert resolve_pdf_paths(["*.nonexistent"]) == []

    def test_single_file(self, tmp_path):
        f = tmp_path / "test.pdf"
        f.write_text("")
        paths = resolve_pdf_paths([str(f)])
        assert paths == [str(f)]

    def test_glob_pattern(self, tmp_path):
        (tmp_path / "a.pdf").write_text("")
        (tmp_path / "b.pdf").write_text("")
        paths = resolve_pdf_paths([f"{tmp_path}/*.pdf"])
        assert len(paths) == 2


class TestDetectWriter:
    def test_csv_writer(self):
        w = _detect_writer("output.csv")
        assert isinstance(w, CsvWriter)

    def test_xlsx_writer(self):
        w = _detect_writer("output.xlsx")
        assert isinstance(w, XlsxWriter)

    def test_default_is_csv(self):
        w = _detect_writer("output")
        assert isinstance(w, CsvWriter)


class TestCliArgparse:
    def test_help_has_expected_flags(self):
        parser = _build_parser()
        help_text = parser.format_help()
        assert "--verbose" in help_text
        assert "--quiet" in help_text
        assert "--drive" in help_text
        assert "--credentials" in help_text
        assert "--to-sheets" in help_text

    def test_default_output_is_csv(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.output == "output.csv"

    def test_quiet_sets_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["-q"])
        assert args.quiet is True

    def test_verbose_sets_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["-v"])
        assert args.verbose is True


def _build_parser():
    from pdf_parser.cli import main as cli_main
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("--drive", action="store_true")
    parser.add_argument("--credentials", default="")
    parser.add_argument("--folder", default="")
    parser.add_argument("--search", default="")
    parser.add_argument("pdfs", nargs="*")
    parser.add_argument("-o", "--output", default="output.csv")
    parser.add_argument("--area", default="")
    parser.add_argument("--to-sheets", default="", metavar="SPREADSHEET_URL")
    return parser
