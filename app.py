import csv
import re
from pathlib import Path

def extract_submission_pdfs(base_dir: str, year: str, output_csv: str):
    """
    Traverses a structured directory to find specific PDF files and logs them to a CSV.
    
    Args:
        base_dir (str): The root path containing the year folders.
        year (str): The specific year folder to process (e.g., '2026').
        output_csv (str): The path where the output CSV will be saved.
    """
    base_path = Path(base_dir)
    year_path = base_path / year
    
    # Validate base path
    if not year_path.exists() or not year_path.is_dir():
        print(f"Error: The directory {year_path} does not exist.")
        return

    results = []
    
    # Regex to ensure the folder is an 8-digit date (mmddyyyy)
    date_folder_pattern = re.compile(r"^\d{8}$")

    print(f"Scanning directory: {year_path}...")

    # 1. Iterate through State folders (e.g., NY, CA)
    for state_dir in year_path.iterdir():
        if not state_dir.is_dir():
            continue
            
        state_name = state_dir.name
        
        # 2. Iterate through Date folders inside the State folder
        for date_dir in state_dir.iterdir():
            if not date_dir.is_dir() or not date_folder_pattern.match(date_dir.name):
                continue
                
            date_str = date_dir.name
            
            # 3. Find all "For Submission" folders deep inside this date folder
            for submission_dir in date_dir.rglob("For Submission"):
                if not submission_dir.is_dir():
                    continue
                    
                # 4. Find all PDFs recursively within the "For Submission" folder
                for file_path in submission_dir.rglob("*"):
                    # Check if it's a file and a PDF (case-insensitive)
                    if file_path.is_file() and file_path.suffix.lower() == '.pdf':
                        
                        # Check if the filename (without the .pdf extension) ends with the date string
                        if file_path.stem.endswith(date_str):
                            # Append the matched record
                            results.append([
                                state_name,
                                date_str,
                                file_path.name,
                                str(file_path.resolve()) # Gets the absolute full path
                            ])

    # 5. Write the extracted data to a CSV file
    try:
        with open(output_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Write headers
            writer.writerow(['State Name', 'Date of Folder', 'PDF File Name', 'PDF Full Path'])
            # Write data rows
            writer.writerows(results)
            
        print(f"Success: Processed and saved {len(results)} records to '{output_csv}'.")
    except PermissionError:
        print(f"Error: Permission denied when trying to write to {output_csv}. Ensure the file is not open in another program.")

# ==========================================
# Execution Example
# ==========================================
if __name__ == "__main__":
    # Update these variables with your actual paths
    ROOT_FOLDER_LOCATION = r"C:\Path\To\Your\Main\Folder"  # Use raw string 'r' for Windows paths
    TARGET_YEAR = "2026"
    OUTPUT_CSV_FILE = "submission_pdfs_report.csv"

    extract_submission_pdfs(ROOT_FOLDER_LOCATION, TARGET_YEAR, OUTPUT_CSV_FILE)