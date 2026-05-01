from pathlib import Path
import csv
import os

try:
    import pandas as pd
except ImportError:
    pd = None


def find_year_ending_pdfs(input_location, year, output_name=None):
    """
    Scan this structure:

        input_location/year/state_folders/**/*

    The scan goes through every nested folder under each state folder.
    There is no fixed limit on folder depth and no limit on number of PDFs.

    Finds every PDF file where the file name, without ".pdf",
    ends with the selected year.

    Example:
        report_2026.pdf      -> selected
        report_2026_final.pdf -> not selected
        report_2025.pdf      -> not selected when year is 2026

    Output columns:
        state_name
        file_path
        file_name
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

    for state_folder in year_folder.iterdir():
        if not state_folder.is_dir():
            continue

        state_name = state_folder.name

        def remember_skipped_folder(error):
            skipped_folders.append(error.filename)

        for current_folder, _, file_names in os.walk(
            state_folder, onerror=remember_skipped_folder
        ):
            current_folder = Path(current_folder)

            for file_name in file_names:
                pdf_file = current_folder / file_name

                if pdf_file.suffix.lower() != ".pdf":
                    continue

                if pdf_file.stem.strip().endswith(year):
                    results.append(
                        {
                            "state_name": state_name,
                            "file_path": str(pdf_file.resolve()),
                            "file_name": pdf_file.name,
                        }
                    )

    results.sort(key=lambda row: (row["state_name"], row["file_path"]))

    if output_name is None:
        output_name = f"pdf_files_ending_with_{year}"

    output_csv = input_location / f"{output_name}.csv"
    output_excel = input_location / f"{output_name}.xlsx"

    columns = ["state_name", "file_path", "file_name"]

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
