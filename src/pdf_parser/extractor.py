import re
import pdfplumber


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


def extract_pdf_data(pdf_path):
    lines_by_page = get_pdf_lines(pdf_path)
    page_texts = get_page_texts(pdf_path)
    page0 = lines_by_page[0] if lines_by_page else []

    site_id = find_header_value(page0, "Site ID")
    site_name = find_header_value(page0, "Site Name")
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
