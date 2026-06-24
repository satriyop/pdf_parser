# pdf-parser

Parse Energy Saving Survey PDFs to CSV, XLSX, or Google Sheets.

Extracts site data (ID, name, phase, power readings, coordinates) from structured survey PDFs and outputs clean spreadsheets. Supports Google Drive ingestion with crash-resilient streaming.

## Quick Start

```bash
bash setup.sh
source venv/bin/activate
pdf-parser "*.pdf" -o hasil.xlsx --area "EAST JAVA"
```

## Features

- **Single/batch** — one PDF or glob pattern (`*.pdf`)
- **CSV/XLSX/Sheets** — auto-detect format from `-o` extension, or `--to-sheets`
- **XLSX sheets** — per-area sheets, appendable across runs
- **GPS coordinates** — extracted from photo overlays via OCR
- **Google Drive** — recursive folder scan, search, interactive pick
- **Crash recovery** — progress checkpoint per file, retry skips done files
- **Streaming** — download → parse → delete one file at a time (peak disk ~3 MB)
- **Config file** — TOML-based defaults for credentials, area, output
- **Verbose/quiet** — `-v` for OCR debug, `-q` for minimal output

## Usage

```bash
# Local files
pdf-parser survey.pdf -o output.csv
pdf-parser "*.pdf" -o output.xlsx --area "EAST JAVA"

# Google Drive  
pdf-parser --drive --folder FOLDER_ID -o hasil.xlsx
pdf-parser --drive --search "BAYEMAN" -o hasil.csv
pdf-parser --drive -o hasil.xlsx                        # interactive pick
pdf-parser --drive --folder FOLDER_ID --search "SURVEY"  # filtered recursive

# Google Sheets (share sheet with SA email first)
pdf-parser --drive --search "Survey" --to-sheets "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID"
pdf-parser --drive --folder FOLDER_ID --to-sheets "https://docs.google.com/spreadsheets/d/SPREADSHEET_ID"

# Flags
pdf-parser -v "*.pdf" -o debug.xlsx              # verbose OCR debug
pdf-parser -q --drive --folder X -o hasil.xlsx   # quiet, summary only
```

## Google Sheets Output

### Setup

1. Create a new Google Sheet in your Drive
2. Share it with your Service Account email as **Editor**:
   ```
   pdf-parser-sa@nex-project-500312.iam.gserviceaccount.com
   ```
3. Use the sheet URL:
   ```bash
   # Search by name across all drive
   pdf-parser --drive --search "Survey" --to-sheets "https://docs.google.com/spreadsheets/d/abc123..."

   # Or scan a specific folder recursively (all subfolders)
   pdf-parser --drive --folder FOLDER_ID --to-sheets "https://docs.google.com/spreadsheets/d/abc123..."
   ```

### Behavior

- Each `--area` becomes a separate sheet tab within the spreadsheet
- Running again with the same `--area` **appends** rows to the existing sheet
- Running with a different `--area` **creates a new tab**

## Crash Recovery

When processing many files, progress is tracked per-file in `{output}.progress.json`.

```bash
# First run: process 800/1207 files → crash
pdf-parser --drive --folder FOLDER_ID -o hasil.xlsx
pdf-parser --drive --folder FOLDER_ID --to-sheets "https://docs.google.com/spreadsheets/d/SHEET_ID"
# ... crash at file #801 ...

# Retry: skips first 800 files, resumes from #801
pdf-parser --drive --folder FOLDER_ID -o hasil.xlsx
pdf-parser --drive --folder FOLDER_ID --to-sheets "https://docs.google.com/spreadsheets/d/SHEET_ID"
```

`progress.json` is safe to delete — just clears the checkpoint.

## Google Drive Setup

### 1. Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → **APIs & Services** → **Library**
3. Enable **Google Drive API** and **Google Sheets API**
4. **Credentials** → **+ Create Credentials** → **Service Account**
5. **Credentials** → click SA → **Keys** → **Add Key** → **Create New Key** → **JSON**
6. File downloads as `*.json` — store securely

### 2. Store Key Securely

```bash
mkdir -p ~/.config/pdf-parser
mv ~/Downloads/project-*.json ~/.config/pdf-parser/key.json

# .gitignore already blocks *.json — key won't be committed
```

First run auto-creates `~/.config/pdf-parser/config.toml` with the key path detected.

### 3. Share Drive Folder

1. Open your Google Drive folder
2. **Share** → add service account email (from JSON: `client_email`)
3. Permission: **Viewer**

### 4. Find Folder ID

From the folder URL:
```
https://drive.google.com/drive/folders/18_IigpLFRizYFBSNYgCyd9zoFuM0XqIc
                                      └──────────────────────────────┘
                                        this is the FOLDER_ID
```

## Config File (`pdf_parser.toml`)

Location (searched in order):
1. `./pdf_parser.toml` (project-level, overrides user config)
2. `~/.config/pdf-parser/config.toml` (user-level)

```toml
[google]
credentials = "/home/user/.config/pdf-parser/key.json"

[defaults]
area = "EAST JAVA"
output = "output.xlsx"

[drive]
last_folder = "18_IigpLFRizYFBSNYgCyd9zoFuM0XqIc"
```

CLI flags always override config values.

## Requirements

- Python ≥ 3.10
- Tesseract OCR (`apt install tesseract-ocr`)
- Poppler utils (`apt install poppler-utils`)
- Google Service Account JSON key (for Drive/Sheets mode)

## Deploy (Ubuntu)

```bash
git clone <repo>
cd pdf-parser
bash setup.sh   # installs deps, creates venv
source venv/bin/activate
pdf-parser "*.pdf" -o hasil.xlsx --area "EAST JAVA"
```

## Tests

```bash
pip install -e ".[test]"
pytest -v
```

## Project Structure

```
src/pdf_parser/
├── __init__.py
├── cli.py           # argument parsing, pipeline orchestration
├── config.py        # TOML config loader
├── extractor.py     # pdfplumber text extraction
├── googledrive.py   # Google Drive API + streaming context managers
├── gps.py           # image OCR for GPS coordinates
├── models.py        # SiteData dataclass
├── progress.py      # crash recovery tracker
├── sheets.py        # Google Sheets writer
└── writers.py       # CSV / XLSX output writers
```
