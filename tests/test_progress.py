import json
import os

import pytest

from pdf_parser.progress import ProgressTracker


class TestProgressTracker:
    def test_new_tracker_has_empty_processed(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        assert tracker.done_count() == 0
        assert tracker.data["processed"] == []

    def test_is_done(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        assert not tracker.is_done("file_1")
        tracker.mark_done("file_1")
        assert tracker.is_done("file_1")

    def test_marks_done_and_persists(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        tracker.mark_done("file_a")
        tracker.mark_done("file_b")

        progress_file = tmp_path / "out.csv.progress.json"
        assert progress_file.exists()
        data = json.loads(progress_file.read_text())
        assert data["processed"] == ["file_a", "file_b"]

    def test_reloads_existing_progress(self, tmp_path):
        out = tmp_path / "out.csv"
        progress_file = tmp_path / "out.csv.progress.json"
        progress_file.write_text(json.dumps({"context": "", "processed": ["f1", "f2"]}))

        tracker = ProgressTracker(str(out))
        assert tracker.done_count() == 2
        assert tracker.is_done("f1")
        assert tracker.is_done("f2")
        assert not tracker.is_done("f3")

    def test_double_mark_does_not_duplicate(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        tracker.mark_done("x")
        tracker.mark_done("x")

        assert tracker.done_count() == 1

    def test_remaining_filters_done(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        tracker.mark_done("a")
        tracker.mark_done("b")

        files = [{"id": "a"}, {"id": "b"}, {"id": "c"}, {"id": "d"}]
        remaining = tracker.remaining(files)
        assert [f["id"] for f in remaining] == ["c", "d"]

    def test_clear_removes_progress_file(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        tracker.mark_done("x")
        assert os.path.exists(tracker.path)
        tracker.clear()
        assert not os.path.exists(tracker.path)

    def test_remaining_all_done(self, tmp_path):
        out = tmp_path / "out.csv"
        tracker = ProgressTracker(str(out))
        tracker.mark_done("a")
        tracker.mark_done("b")
        remaining = tracker.remaining([{"id": "a"}, {"id": "b"}])
        assert remaining == []
