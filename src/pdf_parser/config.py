import os
import tomllib
from pathlib import Path


def _find_config():
    candidates = [
        Path("pdf_parser.toml"),
        Path.home() / ".config" / "pdf-parser" / "config.toml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def load_config():
    path = _find_config()
    if not path:
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def apply_config(args, config):
    if not config:
        return args

    google = config.get("google", {})
    defaults = config.get("defaults", {})

    if not args.credentials:
        args.credentials = google.get("credentials", "")
    if not args.folder:
        args.folder = config.get("drive", {}).get("last_folder", "")
    if not args.area:
        args.area = defaults.get("area", "")
    if args.output == "output.csv" and "output" in defaults:
        args.output = defaults["output"]

    return args


def create_default_config():
    dest = Path.home() / ".config" / "pdf-parser" / "config.toml"
    if dest.exists():
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    key_dir = Path.home() / ".config" / "pdf-parser"
    key_files = list(key_dir.glob("*.json"))
    key_path = str(key_files[0]) if key_files else ""

    content = f"""# pdf-parser configuration
# See https://github.com/satriyop/pdf_parser for docs

[google]
credentials = "{key_path}"

[defaults]
area = ""
output = "output.xlsx"

# [drive]
# last_folder = ""
"""
    dest.write_text(content)
    return dest
