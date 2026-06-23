#!/usr/bin/env bash
set -euo pipefail

echo "=== pdf-parser setup ==="

# --- System dependencies ---
echo "[1/4] Installing system packages..."
if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        python3-venv \
        python3-pip \
        tesseract-ocr \
        poppler-utils
elif command -v brew &>/dev/null; then
    brew list tesseract &>/dev/null || brew install tesseract
    brew list poppler &>/dev/null || brew install poppler
else
    echo "Warning: unknown package manager. Install tesseract-ocr and poppler-utils manually."
fi

# --- Python virtual environment ---
echo "[2/4] Creating virtual environment..."
python3 -m venv venv

# --- Install Python packages ---
echo "[3/4] Installing Python packages..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# --- Install package in editable mode ---
echo "[4/4] Installing pdf-parser..."
pip install -q -e .

echo ""
echo "=== Setup complete ==="
echo ""
echo "Usage:"
echo "  source venv/bin/activate"
echo "  pdf-parser input.pdf -o output.csv --area \"EAST JAVA\""
echo "  # or"
echo "  python -m pdf_parser input.pdf -o output.csv"
