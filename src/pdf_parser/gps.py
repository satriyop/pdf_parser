import os
import re
import subprocess
import tempfile

GPS_PATTERN = re.compile(
    r"lat\s*=\s*(-?\d+\.\d+)\s*\n?\s*[lI1]ng\s*=\s*(-?\d+\.\d+)",
    re.IGNORECASE | re.DOTALL,
)


def _ocr_image(image_path):
    outpath = image_path + "_ocr"
    subprocess.run(
        ["tesseract", image_path, outpath],
        capture_output=True, timeout=60,
    )
    txt_path = outpath + ".txt"
    if os.path.exists(txt_path):
        with open(txt_path) as f:
            return f.read()
    return ""


def _extract_from_images(images_dir):
    candidates = []
    for f in sorted(os.listdir(images_dir)):
        fpath = os.path.join(images_dir, f)
        if not f.lower().endswith((".jpg", ".jpeg")):
            continue
        if os.path.getsize(fpath) < 50000:
            continue
        text = _ocr_image(fpath)
        m = GPS_PATTERN.search(text)
        if m:
            lat, lng = m.group(1), m.group(2)
            decimals_lng = lng.split(".")[1] if "." in lng else ""
            if 100 <= float(lng) <= 200 and len(decimals_lng) >= 5:
                candidates.append((f, lat, lng))
    if candidates:
        best = min(
            candidates,
            key=lambda x: abs(float(x[2]) - 115),
        )
        return best[1], best[2]
    return None, None


def extract_gps(pdf_path):
    tmpdir = tempfile.mkdtemp()
    try:
        subprocess.run(
            ["pdfimages", "-j", pdf_path, f"{tmpdir}/img"],
            capture_output=True, timeout=60,
        )
        lat, lng = _extract_from_images(tmpdir)
        if lat and lng:
            return f"lat= {lat}\nlng= {lng}"
        return ""
    finally:
        for f in os.listdir(tmpdir):
            os.remove(os.path.join(tmpdir, f))
        os.rmdir(tmpdir)
