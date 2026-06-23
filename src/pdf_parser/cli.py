import argparse
import glob
import os
import sys

from googleapiclient.errors import HttpError
from tqdm import tqdm

from .config import load_config, apply_config, create_default_config
from .extractor import extract_pdf_data
from .gps import extract_gps
from .models import SiteData
from .progress import ProgressTracker
from .writers import CsvWriter, XlsxWriter
from .googledrive import stream_pdf_dir, DriveClient


VERBOSE = False


def parse_single_pdf(pdf_path, area_name="", no=1):
    data = extract_pdf_data(pdf_path)
    coord = extract_gps(pdf_path, verbose=VERBOSE)

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


def _write_site(writer, site):
    writer.write_one(site)


def main():
    global VERBOSE

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

    # --- Global flags ---
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Show detailed debug output",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress progress output, show only results",
    )

    # --- Drive flags ---
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
    VERBOSE = args.verbose

    # --- Load config ---
    config = load_config()
    args = apply_config(args, config)

    # --- Create default config if none exists ---
    if not config:
        created = create_default_config()
        if created and not args.quiet:
            print(f"Created default config: {created}")

    writer = None
    sheet_name = args.area or "Survey Data"

    # --- Route: Google Drive or local files ---
    if args.drive:
        if not args.quiet:
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
            if args.folder and args.verbose:
                print(f"\nInspecting folder tree (max depth 3):")
                try:
                    tree = client.inspect_folder(args.folder, max_depth=3)
                    for line in tree:
                        print(line)
                except Exception as e:
                    print(f"Could not inspect folder: {e}")
            print("No files selected.")
            sys.exit(0)

        if not args.quiet:
            print(f"\nSelected {len(selected)} file(s). Processing ...")

        tracker = ProgressTracker(args.output)
        remaining = tracker.remaining(selected)
        skipped = len(selected) - len(remaining)

        if skipped and not args.quiet:
            print(f"  Skipping {skipped} already-processed file(s).")

        all_sites = []
        errors = []
        writer = _detect_writer(args.output)
        total = len(remaining)
        done_count = tracker.done_count()

        with stream_pdf_dir(client, remaining) as streamer:
            iterator = tqdm(streamer, desc="Parsing", unit="file",
                            total=total, disable=args.quiet,
                            initial=0)
            for pdf_path, file_id in iterator:
                iterator.set_postfix(file=os.path.basename(pdf_path)[:40])
                try:
                    no = done_count + len(all_sites) + 1
                    site = parse_single_pdf(pdf_path, area_name=args.area, no=no)
                    _write_site(writer, site)
                    all_sites.append(site)
                    tracker.mark_done(file_id)
                except Exception as e:
                    errors.append((os.path.basename(pdf_path), str(e)))

        if not args.quiet:
            print()
    else:
        pdf_paths = resolve_pdf_paths(args.pdfs)
        if not pdf_paths:
            print("Error: no PDF files found. Use --drive for Google Drive.", file=sys.stderr)
            sys.exit(1)

        if not args.quiet:
            print(f"Found {len(pdf_paths)} PDF(s)")

        all_sites = []
        errors = []

        writer = _detect_writer(args.output)
        iterator = tqdm(pdf_paths, desc="Parsing", unit="file", disable=args.quiet)
        for i, pdf_path in enumerate(iterator, 1):
            iterator.set_postfix(file=os.path.basename(pdf_path)[:40])
            try:
                site = parse_single_pdf(pdf_path, area_name=args.area, no=i)
                _write_site(writer, site)
                all_sites.append(site)
            except Exception as e:
                errors.append((os.path.basename(pdf_path), str(e)))

        if not args.quiet:
            print()

    # Close writer if XLSX
    if writer and isinstance(writer, XlsxWriter):
        writer.close()

    # --- Google Sheets output ---
    if args.to_sheets:
        if not args.credentials:
            print("Error: --credentials required with --to-sheets", file=sys.stderr)
            sys.exit(1)

        sa_email = "pdf-parser-sa@nex-project-500312.iam.gserviceaccount.com"
        from .sheets import SheetsWriter

        try:
            if not args.quiet:
                print("Writing to Google Sheets ...")
            sheets_writer = SheetsWriter(args.credentials, spreadsheet_url=args.to_sheets)
            sheets_writer.write(all_sites, sheet_name=sheet_name)
        except HttpError as e:
            status = e.resp.status if hasattr(e, "resp") else 0
            if status == 403:
                print(f"\nERROR: Access denied (403). Share your sheet with:")
                print(f"  {sa_email}")
                print(f"  (Go to sheet → Share → add that email as Editor)")
            elif status == 404:
                print(f"\nERROR: Spreadsheet not found (404). Check the URL.")
            elif status == 429:
                print(f"\nERROR: Google API quota exceeded.")
                print(f"  Try again later, or use -o output.xlsx instead.")
            else:
                print(f"\nERROR: Google Sheets API error: {e}")
            print(f"\nFallback: data is also saved to {args.output}")
            sys.exit(1)

    # --- Summary ---
    succeeded = len(all_sites)
    failed = len(errors)
    if args.quiet:
        print(f"{succeeded} succeeded, {failed} failed")
    else:
        print(f"Done. {succeeded} succeeded, {failed} failed.")

    if errors and not args.quiet:
        print("\nFailed files:")
        for name, reason in errors:
            print(f"  - {name}: {reason}")
