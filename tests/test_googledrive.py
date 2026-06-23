import os
from unittest.mock import patch, MagicMock

import pytest

from pdf_parser.googledrive import temp_pdf_dir


class FakeClient:
    def download_selected(self, files, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        for f in files:
            path = os.path.join(dest_dir, f["name"])
            with open(path, "w") as fh:
                fh.write("fake pdf")
        return [os.path.join(dest_dir, f["name"]) for f in files]

    def download(self, file_id, dest_path):
        pass


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
