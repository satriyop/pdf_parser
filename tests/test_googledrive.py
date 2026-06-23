import os
from unittest.mock import patch, MagicMock

import pytest

from pdf_parser.googledrive import temp_pdf_dir, stream_pdf_dir


class FakeClient:
    def download_selected(self, files, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        for f in files:
            path = os.path.join(dest_dir, f["name"])
            with open(path, "w") as fh:
                fh.write("fake pdf")
        return [os.path.join(dest_dir, f["name"]) for f in files]

    def download(self, file_id, dest_path):
        with open(dest_path, "w") as fh:
            fh.write("fake pdf")


class TestTempPdfDir:
    def test_yields_downloaded_paths(self):
        client = FakeClient()
        selected = [{"name": "a.pdf", "id": "1"}, {"name": "b.pdf", "id": "2"}]

        with temp_pdf_dir(client, selected) as paths:
            assert len(paths) == 2
            assert all(p.endswith(".pdf") for p in paths)
            assert all(os.path.exists(p) for p in paths)

    def test_cleans_up_on_normal_exit(self):
        client = FakeClient()
        selected = [{"name": "test.pdf", "id": "1"}]

        with temp_pdf_dir(client, selected) as paths:
            tmpdir = os.path.dirname(paths[0])
            assert os.path.isdir(tmpdir)

        assert not os.path.isdir(tmpdir)

    def test_cleans_up_on_pipeline_exception(self):
        client = FakeClient()
        selected = [{"name": "crash.pdf", "id": "1"}]

        with pytest.raises(RuntimeError):
            with temp_pdf_dir(client, selected) as paths:
                tmpdir = os.path.dirname(paths[0])
                raise RuntimeError("process failed")

        assert not os.path.isdir(tmpdir)

    def test_cleans_up_on_download_failure(self):
        class BrokenClient:
            def download_selected(self, files, dest_dir):
                raise ConnectionError("drive unavailable")

        with pytest.raises(ConnectionError):
            with temp_pdf_dir(BrokenClient(), [{"name": "x.pdf", "id": "1"}]):
                pass

    def test_handles_empty_selected(self):
        client = FakeClient()
        with temp_pdf_dir(client, []) as paths:
            assert paths == []


class TestStreamPdfDir:
    def test_streams_one_file_at_a_time(self):
        client = FakeClient()
        selected = [
            {"name": "a.pdf", "id": "1"},
            {"name": "b.pdf", "id": "2"},
            {"name": "c.pdf", "id": "3"},
        ]

        seen = []
        with stream_pdf_dir(client, selected) as streamer:
            for pdf_path, file_id in streamer:
                seen.append((file_id, os.path.basename(pdf_path)))
                assert os.path.exists(pdf_path)

        assert seen == [("1", "a.pdf"), ("2", "b.pdf"), ("3", "c.pdf")]

    def test_previous_file_deleted_after_next_yield(self):
        client = FakeClient()
        selected = [{"name": "a.pdf", "id": "1"}, {"name": "b.pdf", "id": "2"}]

        prev = None
        with stream_pdf_dir(client, selected) as streamer:
            for pdf_path, _ in streamer:
                if prev:
                    assert not os.path.exists(prev)
                prev = pdf_path

    def test_last_file_deleted_after_iteration_ends(self):
        client = FakeClient()
        selected = [{"name": "only.pdf", "id": "1"}]

        last = None
        with stream_pdf_dir(client, selected) as streamer:
            for pdf_path, _ in streamer:
                last = pdf_path
                assert os.path.exists(pdf_path)

        assert last and not os.path.exists(last)

    def test_tmpdir_cleaned_after_exit(self):
        client = FakeClient()
        selected = [{"name": "x.pdf", "id": "99"}]

        tmpdir = None
        with stream_pdf_dir(client, selected) as streamer:
            for pdf_path, _ in streamer:
                tmpdir = os.path.dirname(pdf_path)

        assert not os.path.isdir(tmpdir)

    def test_cleans_up_on_exception(self):
        client = FakeClient()
        selected = [{"name": "crash.pdf", "id": "1"}]

        with pytest.raises(RuntimeError):
            with stream_pdf_dir(client, selected) as streamer:
                for pdf_path, _ in streamer:
                    raise RuntimeError("boom")

    def test_handles_empty_selected(self):
        client = FakeClient()
        with stream_pdf_dir(client, []) as streamer:
            count = sum(1 for _ in streamer)
        assert count == 0
