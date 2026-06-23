# pdf-parser

Parse Energy Saving Survey PDFs to CSV or XLSX.

Extracts site data (ID, name, phase, power readings, coordinates) from structured survey PDFs and outputs clean spreadsheets.

## Quick Start

```bash
bash setup.sh
source venv/bin/activate
pdf-parser "*.pdf" -o hasil.xlsx --area "EAST JAVA"
```

## Features

- **Single/batch** — one PDF or glob pattern (`*.pdf`)
- **CSV/XLSX** — auto-detect format from `-o` extension
- **XLSX sheets** — per-area sheets, appendable across runs
- **GPS coordinates** — extracted from photo overlays via OCR
- **Google Drive** — ingest PDFs directly from Drive

## Usage

```bash
# Local files
pdf-parser survey.pdf -o output.csv
pdf-parser "*.pdf" -o output.xlsx --area "EAST JAVA"

# Google Drive
pdf-parser --drive --credentials key.json --folder FOLDER_ID -o hasil.xlsx
pdf-parser --drive --credentials key.json --search "BAYEMAN" -o hasil.csv
pdf-parser --drive --credentials key.json -o hasil.xlsx   # interactive pick

# With env var (no --credentials needed)
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/pdf-parser/key.json
pdf-parser --drive --folder FOLDER_ID -o hasil.xlsx
```

## Google Drive Setup

### 1. Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → **APIs & Services** → **Library**
3. Enable **Google Drive API**
4. **Credentials** → **+ Create Credentials** → **Service Account**
5. Role: **Viewer** → **Done**
6. Tab **Keys** → **Add Key** → **Create New Key** → **JSON**
7. File downloads as `*.json` — store securely

### 2. Store Key Securely

```bash
mkdir -p ~/.config/pdf-parser
mv ~/Downloads/project-*.json ~/.config/pdf-parser/key.json

# .gitignore already blocks *.json — key won't be committed
```

### 3. Share Drive Folder

1. Open your Google Drive folder
2. **Share** → add service account email (found in JSON: `client_email`)
3. Permission: **Viewer**

### 4. Find Folder ID

From the folder URL:
```
https://drive.google.com/drive/folders/18_IigpLFRizYFBSNYgCyd9zoFuM0XqIc
                                      └──────────────────────────────┘
                                        this is the FOLDER_ID
```

## Requirements

- Python ≥ 3.10
- Tesseract OCR (`apt install tesseract-ocr`)
- Poppler utils (`apt install poppler-utils`)
- Google Service Account JSON key (for Drive mode)

## Deploy (Ubuntu)

```bash
git clone <repo>
cd pdf-parser
bash setup.sh   # installs deps, creates venv
source venv/bin/activate
pdf-parser "*.pdf" -o output.xlsx --area "EAST JAVA"
```

## Project Structure

```
src/pdf_parser/
├── __init__.py
├── __main__.py      # python -m pdf_parser
├── cli.py           # argument parsing, pipeline orchestration
├── extractor.py     # pdfplumber text extraction
├── gps.py           # image OCR for GPS coordinates
├── googledrive.py   # Google Drive API client
├── models.py        # SiteData dataclass
└── writers.py       # CSV / XLSX output writers
```
