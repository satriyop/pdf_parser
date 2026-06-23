import os
from pathlib import Path

from pdf_parser.config import load_config, apply_config, create_default_config


class TestLoadConfig:
    def test_no_config_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
        config = load_config()
        assert config == {}

    def test_local_config_overrides(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg_path = tmp_path / "pdf_parser.toml"
        cfg_path.write_text(
            '[google]\ncredentials = "/custom/key.json"\n'
            '[defaults]\narea = "SULAWESI"\noutput = "result.xlsx"\n'
        )
        config = load_config()
        assert config["google"]["credentials"] == "/custom/key.json"
        assert config["defaults"]["area"] == "SULAWESI"


class TestApplyConfig:
    def test_apply_credentials(self):
        class Args:
            credentials = ""
            folder = ""
            area = ""
            output = "output.csv"

        config = {"google": {"credentials": "/key.json"}}
        args = apply_config(Args(), config)
        assert args.credentials == "/key.json"

    def test_cli_overrides_config(self):
        class Args:
            credentials = "/cli/key.json"
            folder = ""
            area = "SULAWESI"
            output = "output.csv"

        config = {"google": {"credentials": "/config/key.json"}}
        args = apply_config(Args(), config)
        assert args.credentials == "/cli/key.json"

    def test_empty_config_unchanged(self):
        class Args:
            credentials = ""
            folder = ""
            area = ""
            output = "output.csv"

        args = apply_config(Args(), {})
        assert args.output == "output.csv"


class TestCreateDefaultConfig:
    def test_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        dest = create_default_config()
        assert dest is not None
        assert dest.exists()
        content = dest.read_text()
        assert "[google]" in content
        assert "[defaults]" in content

    def test_skips_if_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        dest = create_default_config()
        mtime = dest.stat().st_mtime
        create_default_config()
        assert dest.stat().st_mtime == mtime
