"""
PDF Scanner - Scans folder structure and generates CSV report.

Folder structure:
  <BASE_PATH>/<YEAR>/<state>/<mmddyyyy>/[nested folders]/For Submission/[nested]/*.pdf

HOW TO USE:
  Just update the 3 variables in the CONFIG section below, then run:
    python scan_pdfs.py
"""

import os
import re
import csv
from collections import Counter


# ============================================================
#   CONFIG — Update these 3 values before running
# ============================================================

BASE_PATH   = r"C:\Your\Base\Folder"       # Root folder containing year folders
YEAR        = "2026"                        # Year folder to scan
OUTPUT_DIR  = r"C:\Your\Output\Folder"     # Folder where the CSV will be saved

# ============================================================


DATE_FOLDER_RE = re.compile(r"^\d{8}$")


def is_date_folder(name: str) -> bool:
    return bool(DATE_FOLDER_RE.match(name))


def find_matching_pdfs(for_submission_path: str, date_str: str) -> list:
    """
    Recursively walk a 'For Submission' folder.
    Return full paths of PDFs whose base name (without extension) ends with date_str.
    """
    matched = []
    for root, _, files in os.walk(for_submission_path):
        for filename in files:
            if not filename.lower().endswith(".pdf"):
                continue
            name_no_ext = os.path.splitext(filename)[0]
            if name_no_ext.endswith(date_str):
                matched.append(os.path.join(root, filename))
    return matched


def scan(base_path: str, year: str) -> list:
    year_path = os.path.join(base_path, year)

    if not os.path.exists(year_path):
        raise FileNotFoundError(f"Year folder does not exist: {year_path}")
    if not os.path.isdir(year_path):
        raise NotADirectoryError(f"Not a directory: {year_path}")

    records = []

    state_entries = sorted(os.listdir(year_path))
    if not state_entries:
        print(f"  [WARN] No state folders found in: {year_path}")

    for state in state_entries:
        state_path = os.path.join(year_path, state)
        if not os.path.isdir(state_path):
            continue

        print(f"  Scanning state: {state}")
        date_folders_found = 0

        for date_folder in sorted(os.listdir(state_path)):
            date_path = os.path.join(state_path, date_folder)
            if not os.path.isdir(date_path):
                continue
            if not is_date_folder(date_folder):
                print(f"    [SKIP] Not a date folder: {date_folder}")
                continue

            date_folders_found += 1
            date_str = date_folder
            print(f"    Date folder: {date_folder}")

            for root, dirs, _ in os.walk(date_path):
                for d in list(dirs):
                    if d.lower() == "for submission":
                        for_sub_path = os.path.join(root, d)
                        print(f"      Found 'For Submission': {for_sub_path}")
                        pdfs = find_matching_pdfs(for_sub_path, date_str)
                        print(f"        Matching PDFs: {len(pdfs)}")
                        for pdf_path in pdfs:
                            records.append({
                                "State Name":     state,
                                "Date of Folder": date_str,
                                "PDF File Name":  os.path.basename(pdf_path),
                                "PDF Full Path":  pdf_path,
                            })

        if date_folders_found == 0:
            print(f"    [WARN] No valid date folders (mmddyyyy) found in state: {state}")

    return records


def write_csv(records: list, output_path: str):
    fieldnames = ["State Name", "Date of Folder", "PDF File Name", "PDF Full Path"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def main():
    base_path  = os.path.abspath(BASE_PATH)
    year       = YEAR.strip()
    output_dir = os.path.abspath(OUTPUT_DIR)
    output_csv = os.path.join(output_dir, f"pdf_report_{year}.csv")

    print("=" * 60)
    print("  PDF Scanner")
    print("=" * 60)
    print(f"  Base path  : {base_path}")
    print(f"  Year       : {year}")
    print(f"  Output CSV : {output_csv}")
    print("=" * 60)

    # Validate output directory
    if not os.path.exists(output_dir):
        print(f"\n[ERROR] Output folder does not exist: {output_dir}")
        return

    try:
        records = scan(base_path, year)
    except (FileNotFoundError, NotADirectoryError) as e:
        print(f"\n[ERROR] {e}")
        return

    print("\n" + "=" * 60)

    if not records:
        print("  No matching PDFs found. Check that:")
        print("    - BASE_PATH and YEAR are correct")
        print("    - Date folders follow mmddyyyy format (e.g. 03112026)")
        print("    - A 'For Submission' folder exists under each date folder")
        print("    - PDF filenames end with the date (e.g. Report_03112026.pdf)")
    else:
        write_csv(records, output_csv)
        print(f"  Done! {len(records)} PDF(s) found.")
        print(f"  CSV saved to: {output_csv}")

        state_counts = Counter(r["State Name"] for r in records)
        print("\n  Summary by state:")
        for state, count in sorted(state_counts.items()):
            print(f"    {state:10s}: {count} PDF(s)")

    print("=" * 60)


if __name__ == "__main__":
    main()