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

- **Single/batch** — accept one PDF or glob pattern (`*.pdf`)
- **CSV/XLSX** — auto-detect format from `-o` extension
- **XLSX sheets** — per-area sheets, appendable across runs
- **GPS coordinates** — extracted from photo overlays via OCR
- **Google Drive** — ingest PDFs via `--drive --credentials key.json`

## Usage

```bash
# Local files
pdf-parser survey.pdf -o output.csv
pdf-parser "*.pdf" -o output.xlsx --area "EAST JAVA"

# Google Drive
pdf-parser --drive --credentials key.json --folder FOLDER_ID -o hasil.xlsx --area "EAST JAVA"
pdf-parser --drive --credentials key.json --search "Survey" -o hasil.csv
pdf-parser --drive --credentials key.json -o hasil.xlsx   # interactive pick
```

## Requirements

- Python ≥ 3.10
- Tesseract OCR (`apt install tesseract-ocr`)
- Poppler utils (`apt install poppler-utils`)
- Google Service Account key (for Drive mode)

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
