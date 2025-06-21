# main.py
import sys
from typing import Optional, Tuple
from pathlib import Path
from screener_navigator import download_excel_for_stock
from excel_processor import process_and_save_excel

def run_data_pipeline(stock_ticker: str) -> Optional[Tuple[Path, str]]:
    """
    Runs the full data pipeline: downloads the Excel file and processes it into a clean CSV.

    Args:
        stock_ticker (str): The stock ticker to process.

    Returns:
        Optional[Tuple[Path, str]]: A tuple of (processed_csv_path, file_stem) on success, else None.
    """
    print(f"===== STARTING DATA PIPELINE FOR {stock_ticker.upper()} =====")
    
    # This function uses the synchronous version of the downloader
    raw_excel_path = download_excel_for_stock(stock_ticker)
    
    if raw_excel_path:
        # process_and_save_excel returns a tuple (path, stem)
        result = process_and_save_excel(raw_excel_path)
        if result:
            processed_csv_path, file_stem = result
            print(f"Data pipeline successful. Processed file at: {processed_csv_path}")
            print(f"===== DATA PIPELINE FINISHED FOR {stock_ticker.upper()} =====")
            return processed_csv_path, file_stem
    
    print(f"Data pipeline failed for {stock_ticker.upper()}.")
    print(f"===== DATA PIPELINE FINISHED FOR {stock_ticker.upper()} =====")
    return None

# Main execution block to run the pipeline for a single stock from the command line
if __name__ == '__main__':
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        run_data_pipeline(ticker)
    else:
        print("Please provide a stock ticker.")
        print("Usage: python main.py <STOCK_TICKER>")