import argparse
import glob
import os
import sys
import tempfile

from .extractor import extract_pdf_data
from .gps import extract_gps
from .models import SiteData
from .writers import CsvWriter, XlsxWriter


def parse_single_pdf(pdf_path, area_name="", no=1):
    data = extract_pdf_data(pdf_path)
    coord = extract_gps(pdf_path)

    return SiteData(
        no=no,
        area=area_name or data.get("region", ""),
        nama_site=data.get("nama_site", ""),
        site_id=data.get("site_id", ""),
        site_type=data.get("site_type", ""),
        jumlah_phase=data.get("jumlah_phase", ""),
        daya_actual_w=data.get("daya_actual_w", ""),
        area_space_m2=data.get("area_space_m2", ""),
        koordinat=coord,
    )


def resolve_pdf_paths(pattern_or_paths):
    paths = []
    for p in pattern_or_paths:
        expanded = glob.glob(p)
        if expanded:
            paths.extend(expanded)
        elif os.path.isfile(p):
            paths.append(p)
        else:
            print(f"Warning: {p} does not match any file", file=sys.stderr)
    return sorted(set(paths))


def _detect_writer(output_path):
    ext = os.path.splitext(output_path)[1].lower()
    if ext == ".xlsx":
        return XlsxWriter(output_path)
    return CsvWriter(output_path)


def _run_pipeline(pdf_paths, area_name, output_path):
    all_sites = []
    for i, pdf_path in enumerate(pdf_paths, 1):
        print(f"[{i}/{len(pdf_paths)}] {os.path.basename(pdf_path)} ...", end=" ")
        try:
            site = parse_single_pdf(pdf_path, area_name=area_name, no=i)
            all_sites.append(site)
            print("OK")
            print(f"       Site: {site.nama_site}")
            print(f"       ID:   {site.site_id}")
            print(f"       Type: {site.site_type}")
            if site.koordinat:
                print(f"       GPS:  {site.koordinat.split(chr(10))[0]}")
            print()
        except Exception as e:
            print(f"FAILED: {e}")
            print()

    sheet_name = area_name or "Survey Data"
    writer = _detect_writer(output_path)
    writer.write(all_sites, sheet_name=sheet_name)
    return all_sites


def main():
    parser = argparse.ArgumentParser(
        description="Parse Energy Saving Survey PDF to CSV or XLSX",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  pdf-parser survey.pdf -o output.csv\n"
            "  pdf-parser \"*.pdf\" -o output.xlsx --area \"EAST JAVA\"\n"
            "  pdf-parser --drive --credentials key.json --search \"Survey\" -o hasil.xlsx\n"
            "  pdf-parser --drive --credentials key.json --search \"Survey\" --to-sheets SHEET_URL\n"
        ),
    )

    # --- Drive flags (optional group) ---
    drive_group = parser.add_argument_group("Google Drive options")
    drive_group.add_argument(
        "--drive", action="store_true",
        help="Fetch PDFs from Google Drive instead of local files",
    )
    drive_group.add_argument(
        "--credentials", default="",
        help="Path to Google Service Account JSON key file",
    )
    drive_group.add_argument(
        "--folder", default="",
        help="Google Drive folder ID to list PDFs from",
    )
    drive_group.add_argument(
        "--search", default="",
        help="Search pattern for filenames in Google Drive",
    )

    # --- Output flags ---
    parser.add_argument(
        "pdfs", nargs="*",
        help="PDF file(s) or glob pattern (local mode only)",
    )
    parser.add_argument(
        "-o", "--output", default="output.csv",
        help="Output path (.csv or .xlsx)",
    )
    parser.add_argument(
        "--area", default="",
        help="Area/region name (e.g., EAST JAVA, BALI NUSRA)",
    )
    parser.add_argument(
        "--to-sheets", default="",
        metavar="SPREADSHEET_URL",
        help="Output to Google Sheets (URL of existing spreadsheet shared with SA)",
    )

    args = parser.parse_args()

    # --- Route: Google Drive or local files ---
    if args.drive:
        from .googledrive import DriveClient

        print("Connecting to Google Drive ...")
        client = DriveClient(credentials_path=args.credentials or None)

        if args.folder or args.search:
            selected = client.list_files(
                folder_id=args.folder or None,
                search=args.search or None,
            )
        else:
            selected = client.pick_interactive(
                folder_id=args.folder or None,
                search=args.search or None,
            )

        if not selected:
            print("No files selected.")
            sys.exit(0)

        print(f"\nSelected {len(selected)} file(s). Downloading ...")
        tmpdir = tempfile.mkdtemp()
        pdf_paths = client.download_selected(selected, tmpdir)
        print()
    else:
        pdf_paths = resolve_pdf_paths(args.pdfs)
        if not pdf_paths:
            print("Error: no PDF files found. Use --drive for Google Drive.", file=sys.stderr)
            sys.exit(1)

    print(f"Found {len(pdf_paths)} PDF(s)")

    all_sites = _run_pipeline(pdf_paths, args.area, args.output)

    # --- Google Sheets output ---
    if args.to_sheets:
        if not args.credentials:
            print("Error: --credentials required with --to-sheets", file=sys.stderr)
            sys.exit(1)
        from .sheets import SheetsWriter
        print("\nWriting to Google Sheets ...")
        writer = SheetsWriter(args.credentials, spreadsheet_url=args.to_sheets)
        sheet_name = args.area or "Survey Data"
        writer.write(all_sites, sheet_name=sheet_name)
        print(f"Done. {len(all_sites)} site(s) written to Google Sheets")
    else:
        print(f"Done. {len(all_sites)} site(s) written to {args.output}")
