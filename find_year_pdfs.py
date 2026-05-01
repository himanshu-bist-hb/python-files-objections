from pathlib import Path
import csv
import os
import re

try:
    import pandas as pd
except ImportError:
    pd = None


SUBMISSION_FOLDER_NAMES = {"forsubmission", "forsubbmision"}


def normalize_folder_name(folder_name):
    return re.sub(r"[^a-z0-9]", "", folder_name.lower())


def extract_mmddyyyy(folder_name):
    """
    Accept folder names like:
        02112026
        02-11-2026
        02_11_2026
        02.11.2026

    Windows folder names cannot contain '/', but this also handles values
    copied from a date like 02/11/2026 by removing separators.
    """

    digits = re.sub(r"\D", "", folder_name)
    if len(digits) != 8:
        return None

    month = int(digits[:2])
    day = int(digits[2:4])

    if not 1 <= month <= 12:
        return None

    if not 1 <= day <= 31:
        return None

    return digits


def extract_ending_mmddyyyy(file_stem):
    match = re.search(r"(\d{8})$", file_stem.strip())
    if not match:
        return None
    return match.group(1)


def find_matching_date_in_ancestors(start_folder, stop_folder, ending_date):
    current_folder = Path(start_folder).resolve()
    stop_folder = Path(stop_folder).resolve()

    while True:
        folder_date = extract_mmddyyyy(current_folder.name)
        if folder_date == ending_date:
            return folder_date

        if current_folder == stop_folder:
            return None

        parent = current_folder.parent
        if parent == current_folder:
            return None

        current_folder = parent


def find_year_ending_pdfs(input_location, year, output_name=None):
    """
    Scan this structure:

        input_location/year/state_folders/**/*

    The scan goes through every nested folder under each state folder.
    There is no fixed limit on folder depth and no limit on number of PDFs.

    Finds PDF files inside "For Submission" or "For Subbmision" folders.
    The submission folder can be at any depth under a state folder.

    A PDF is selected only when:
        1. it is inside a matching submission folder
        2. its file name, without ".pdf", ends with 8 digits
        3. those 8 digits match a parent/grandparent/super-parent date folder

    Example:
        State/02112026/.../For Subbmision/report_02112026.pdf -> selected
        State/02112026/.../For Submission/report_02122026.pdf  -> not selected

    Output columns:
        state_name
        file_path
        file_name
        file_ending_date
    """

    input_location = Path(input_location).expanduser().resolve()
    year = str(year).strip()
    year_folder = input_location / year

    if not year_folder.exists():
        raise FileNotFoundError(f"Year folder not found: {year_folder}")

    if not year_folder.is_dir():
        raise NotADirectoryError(f"Year path is not a folder: {year_folder}")

    results = []
    skipped_folders = []
    matched_pdf_paths = set()

    for state_folder in year_folder.iterdir():
        if not state_folder.is_dir():
            continue

        state_name = state_folder.name

        def remember_skipped_folder(error):
            skipped_folders.append(error.filename)

        for current_folder, _, _ in os.walk(
            state_folder, onerror=remember_skipped_folder
        ):
            current_folder = Path(current_folder)

            if normalize_folder_name(current_folder.name) not in SUBMISSION_FOLDER_NAMES:
                continue

            for submission_folder, _, file_names in os.walk(
                current_folder, onerror=remember_skipped_folder
            ):
                submission_folder = Path(submission_folder)

                for file_name in file_names:
                    pdf_file = submission_folder / file_name

                    if pdf_file.suffix.lower() != ".pdf":
                        continue

                    pdf_file_path = str(pdf_file.resolve())
                    if pdf_file_path in matched_pdf_paths:
                        continue

                    file_ending_date = extract_ending_mmddyyyy(pdf_file.stem)
                    if file_ending_date is None:
                        continue

                    if not file_ending_date.endswith(year):
                        continue

                    matching_folder_date = find_matching_date_in_ancestors(
                        pdf_file.parent, state_folder, file_ending_date
                    )

                    if matching_folder_date is not None:
                        matched_pdf_paths.add(pdf_file_path)
                        results.append(
                            {
                                "state_name": state_name,
                                "file_path": pdf_file_path,
                                "file_name": pdf_file.name,
                                "file_ending_date": file_ending_date,
                            }
                        )

    results.sort(key=lambda row: (row["state_name"], row["file_ending_date"], row["file_path"]))

    if output_name is None:
        output_name = f"pdf_files_ending_with_{year}"

    output_csv = input_location / f"{output_name}.csv"
    output_excel = input_location / f"{output_name}.xlsx"

    columns = ["state_name", "file_path", "file_name", "file_ending_date"]

    if pd is not None:
        df = pd.DataFrame(results, columns=columns)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        df.to_excel(output_excel, index=False)
    else:
        with output_csv.open("w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=columns)
            writer.writeheader()
            writer.writerows(results)
        output_excel = None

    print(f"Total matching PDF files found: {len(results)}")
    print(f"CSV saved at: {output_csv}")

    if output_excel is not None:
        print(f"Excel saved at: {output_excel}")
    else:
        print("Excel not created because pandas/openpyxl is not installed.")
        print("To enable Excel output, run: pip install pandas openpyxl")

    if skipped_folders:
        print(f"Skipped folders due to access/read errors: {len(skipped_folders)}")

    return results


if __name__ == "__main__":
    input_location = input("Enter main input location: ").strip().strip('"')
    year = input("Enter year: ").strip()

    find_year_ending_pdfs(input_location, year)
