import os
import re
import subprocess
import tempfile

import pdfplumber
from PIL import Image


def get_pdf_lines(pdf_path):
    lines_by_page = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            words = page.extract_words(
                keep_blank_chars=True, x_tolerance=3
            )
            page_lines = []
            rows = {}
            for w in words:
                y_key = round(w["top"], 1)
                if y_key not in rows:
                    rows[y_key] = []
                rows[y_key].append((w["x0"], w["text"]))
            for y in sorted(rows.keys()):
                texts = sorted(rows[y], key=lambda x: x[0])
                page_lines.append((y, texts))
            lines_by_page.append(page_lines)
    return lines_by_page


def get_page_texts(pdf_path):
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
    return texts


def _ocr_page(pdf_path, page_num, dpi=200):
    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["pdftoppm", "-png", "-r", str(dpi), "-f", str(page_num), "-l", str(page_num),
             pdf_path, f"{tmpdir}/p"],
            capture_output=True, timeout=60,
        )
        files = [f for f in os.listdir(tmpdir) if f.endswith(".png")]
        if not files:
            return ""
        img = Image.open(os.path.join(tmpdir, files[0]))
        jpg_path = os.path.join(tmpdir, "page.jpg")
        img.save(jpg_path, "JPEG", quality=90)

        outpath = os.path.join(tmpdir, "ocr")
        subprocess.run(
            ["tesseract", jpg_path, outpath],
            capture_output=True, timeout=120,
        )
        txt_path = outpath + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path) as f:
                return f.read()
        return ""
    finally:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)


def _ocr_all_pages(pdf_path, dpi=300):
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        num_pages = len(pdf.pages)
    texts = []
    for i in range(1, num_pages + 1):
        text = _ocr_page(pdf_path, i, dpi=dpi)
        texts.append(text)
    return texts


def _ocr_lines_from_text(texts):
    labels = {"Site ID", "Site Name", "Jumlah Phase"}
    lines_by_page = []
    for text in texts:
        page_lines = []
        for y, line in enumerate(text.split("\n")):
            tokens = line.strip().split()
            if not tokens:
                continue
            words = []
            i = 0
            while i < len(tokens):
                if i + 1 < len(tokens) and f"{tokens[i]} {tokens[i+1]}" in labels:
                    words.append((float(i), f"{tokens[i]} {tokens[i+1]}"))
                    i += 2
                else:
                    words.append((float(i), tokens[i]))
                    i += 1
            page_lines.append((float(y), words))
        lines_by_page.append(page_lines)
    return lines_by_page


def find_header_value(lines, label):
    for y, words in lines:
        for i, (x, t) in enumerate(words):
            if t.strip() == label and i + 1 < len(words):
                return words[i + 1][1]
    return ""


def find_metric_value(lines, label):
    for y, words in lines:
        line_text = " ".join(t for _, t in words)
        if label.lower() in line_text.lower():
            vals = [
                t for x, t in words
                if re.match(r"^-?\d+\.?\d*$", t.strip())
            ]
            if vals:
                return vals[-1]
    return ""


def find_metric_value_v3(text, label):
    """Find metric value in raw page text (V3 format)."""
    for line in text.split("\n"):
        if label.lower() in line.lower():
            vals = re.findall(r"-?\d+\.?\d*", line)
            if vals:
                return vals[-1]
    return ""


def find_site_type_and_area(page_texts):
    site_type = "Outdoor"
    area_space = ""
    for text in page_texts:
        text_lower = text.lower()
        if "shelterless outdoor" in text_lower:
            site_type = "Outdoor"
            m = re.search(
                r"Area\s+sqcm\s+(\d+\.?\d*)", text, re.IGNORECASE
            )
            if m:
                area_sqm = float(m.group(1)) / 10000.0
                area_space = str(round(area_sqm, 1))
            return site_type, area_space
        elif "shelter indoor" in text_lower:
            site_type = "Indoor"
            m = re.search(
                r"Area\s+sqcm\s+(\d+\.?\d*)", text, re.IGNORECASE
            )
            if m:
                area_sqm = float(m.group(1)) / 10000.0
                area_space = str(round(area_sqm, 1))
            return site_type, area_space
    return site_type, area_space


def _is_v3_format(page_texts, pdf_path=None):
    """Detect V3 format by checking for 'Site ID:' or 'IOH_ENERGY_SAVING_SURVEY_V3',
    or by filename pattern ('Energy Saving/Survey' without '.pdf' suffix)."""
    page0_text = page_texts[0] if page_texts else ""
    if "Site ID:" in page0_text or "IOH_ENERGY_SAVING_SURVEY_V3" in page0_text:
        return True
    if pdf_path:
        basename = os.path.basename(pdf_path)
        # V3 filenames: "Energy Saving Survey_PLM-..." or "Energy saving survey_PLM-..."
        if "energy saving survey" in basename.lower():
            return True
    return False


def _find_site_id(text):
    """Extract site ID from text, trying multiple patterns."""
    # Pattern: explicit "Site ID:" label
    m = re.search(r"Site ID:\s*(\S+)", text)
    if m:
        return m.group(1)
    # Pattern: standard site ID format (2 digits + 3 letters + 4 digits)
    # Allow underscore or non-word char as boundary
    m = re.search(r"(?:^|[\s_/])(\d{2}[A-Za-z]{3}\d{4})(?:[\s_/]|$)", text)
    if m:
        return m.group(1)
    return ""


def _extract_v3_data(pdf_path, page_texts):
    """Extract data from V3 format (Energy Saving Survey V3).
    
    V3 has different labels (with colons), no Site Name, no Region,
    no "Input dari PLN - Total", and "Jumlah Phase X Y" layout.
    
    Falls back to OCR if text extraction yields garbled content (CID fonts).
    """
    page0_text = page_texts[0] if page_texts else ""
    site_id = _find_site_id(page0_text)

    # If text is garbled (CID fonts), fall back to OCR
    if not site_id:
        page_texts = _ocr_all_pages(pdf_path)
        page0_text = page_texts[0] if page_texts else ""
        site_id = _find_site_id(page0_text)

    # V3 has no site name field -- use site_id as fallback
    nama_site = site_id
    region = ""
    site_type = "Outdoor"

    # Jumlah Phase: "Jumlah Phase 1 3" - first digit is the value, second is an option
    # Also handles "Jumlah Phase Phase 1" (OCR output)
    jml_phase = ""
    m = re.search(r"Jumlah\s+Phase[^\d]*(\d)\s", page0_text)
    if m:
        jml_phase = m.group(1)

    daya_actual_raw = find_metric_value_v3(page0_text, "Input dari PLN - Total")
    daya_actual = ""
    if daya_actual_raw:
        try:
            daya_actual = str(round(float(daya_actual_raw.replace(",", "."))))
        except ValueError:
            daya_actual = daya_actual_raw

    area_space = ""

    return {
        "nama_site": nama_site,
        "site_id": site_id,
        "region": region,
        "site_type": site_type,
        "jumlah_phase": jml_phase,
        "daya_actual_w": daya_actual,
        "area_space_m2": area_space,
    }


def extract_pdf_data(pdf_path):
    lines_by_page = get_pdf_lines(pdf_path)
    page_texts = get_page_texts(pdf_path)
    page0 = lines_by_page[0] if lines_by_page else []

    # Detect V3 format early
    if _is_v3_format(page_texts, pdf_path):
        return _extract_v3_data(pdf_path, page_texts)

    site_id = find_header_value(page0, "Site ID")
    site_name = find_header_value(page0, "Site Name")

    # Fallback to OCR if text extraction returned no data
    if not site_id and not site_name:
        page_texts = _ocr_all_pages(pdf_path)
        lines_by_page = _ocr_lines_from_text(page_texts)
        page0 = lines_by_page[0] if lines_by_page else []
        site_id = find_header_value(page0, "Site ID")
        site_name = find_header_value(page0, "Site Name")

    # Final fallback: try finding site ID by pattern in OCR text
    # (handles V3 CID-encoded PDFs that bypassed the V3 detection)
    if not site_id:
        for text in page_texts:
            sid = _find_site_id(text)
            if sid:
                site_id = sid
                if not site_name:
                    site_name = site_id
                break

    region = find_header_value(page0, "Region")
    jml_phase = find_metric_value(page0, "Jumlah Phase")
    daya_actual_raw = find_metric_value(
        page0, "Input dari PLN - Total"
    )

    daya_actual = ""
    if daya_actual_raw:
        try:
            daya_actual = str(
                round(float(daya_actual_raw.replace(",", ".")))
            )
        except ValueError:
            daya_actual = daya_actual_raw

    site_type, area_space = find_site_type_and_area(page_texts)

    return {
        "nama_site": site_name,
        "site_id": site_id,
        "region": region,
        "site_type": site_type,
        "jumlah_phase": jml_phase,
        "daya_actual_w": daya_actual,
        "area_space_m2": area_space,
    }
