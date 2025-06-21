# excel_processor.py

import pandas as pd
from pathlib import Path
from typing import Optional, Tuple
import openpyxl

from config import PROCESSED_DATA_DIR, RAW_DATA_DIR

def process_data_sheet(excel_path: Path) -> Optional[pd.DataFrame]:
    """
    Processes the 'Data Sheet' from a downloaded Screener.in Excel file.
    It cleans, transforms, and prepares the data for time-series analysis.
    """
    sheet_name = "Data Sheet"
    header_row_index = 15  # The row where the main data table header is located

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl', header=header_row_index)
        
        # Clean up the DataFrame
        df.dropna(subset=[df.columns[0]], inplace=True) # Drop rows where the first column (Narration) is empty
        if df.empty: return None

        # Format column headers (Date columns)
        new_columns = ["Narration"] + [
            pd.to_datetime(c).strftime('%b-%y') if isinstance(c, pd.Timestamp) else str(c).strip()
            for c in df.columns[1:]
        ]
        df.columns = new_columns
        df = df.set_index("Narration")

        # Handle potential duplicate index names (e.g., 'Other Income')
        if df.index.has_duplicates:
            is_duplicate = df.index.duplicated(keep=False)
            counts = df.groupby(level=0).cumcount()
            new_index = df.index.where(~is_duplicate, df.index + '_' + counts.astype(str))
            df.index = new_index

        # Convert numeric columns from object/string to numeric types
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.replace(',', '', regex=False)
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        df.dropna(how='all', inplace=True) # Drop rows that are entirely empty
        return df
    except ValueError as e: # More specific error for sheet not found
        print(f"Sheet '{sheet_name}' not found in '{excel_path.name}': {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred processing sheet '{sheet_name}' in '{excel_path.name}': {e}")
        return None

def process_and_save_excel(raw_file_path: Path, specific_save_path: Optional[Path] = None) -> Optional[Tuple[Path, str]]:
    """
    Takes a raw excel file, processes it, saves it as a CSV, and returns the path.

    Args:
        raw_file_path (Path): Path to the raw .xlsx file.
        specific_save_path (Optional[Path]): If provided, saves the CSV to this exact path.
                                             Otherwise, a path is generated automatically.

    Returns:
        Optional[Tuple[Path, str]]: A tuple of (saved_csv_path, original_file_stem) on success, else None.
    """
    print(f"\n--- Starting Excel Processing for: {raw_file_path.name} ---")
    if not raw_file_path or not raw_file_path.is_file():
        print(f"Error: Invalid or non-existent file path provided: {raw_file_path}")
        return None

    processed_df = process_data_sheet(raw_file_path)

    if processed_df is not None:
        file_stem = raw_file_path.stem
        
        # Use the specific save path if provided; otherwise, create a name from the raw file stem.
        save_path = specific_save_path
        if not save_path:
            processed_filename = f"processed_{file_stem}.csv"
            save_path = PROCESSED_DATA_DIR / processed_filename
        
        processed_df.to_csv(save_path)
        print(f"Successfully processed and saved data to: {save_path.name}")
        return save_path, file_stem
    else:
        print(f"Processing failed for '{raw_file_path.name}'. No data frame was generated.")
        return None

# Main execution block for direct testing
if __name__ == '__main__':
    print("--- Running excel_processor.py directly for testing ---")
    try:
        excel_files = sorted(RAW_DATA_DIR.glob('*.xlsx'), key=lambda x: x.stat().st_mtime, reverse=True)
        if excel_files:
            latest_file = excel_files[0]
            print(f"Found latest file to process: {latest_file.name}")
            process_and_save_excel(latest_file)
        else:
            print(f"No Excel files found in {RAW_DATA_DIR} to test.")
    except Exception as e:
        print(f"An error occurred during the test run: {e}")