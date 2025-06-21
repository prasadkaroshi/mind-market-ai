# run_pipeline_standalone.py (Restore this file)

import sys
import asyncio
from pathlib import Path
from screener_navigator import download_excel_for_stock_async
from excel_processor import process_and_save_excel

async def main():
    """
    Main async function to run the full data pipeline.
    This script is called by other parts of the application as a separate process.
    """
    if len(sys.argv) < 2:
        print("FAILURE: No stock ticker provided.")
        sys.exit(1)
        
    stock_ticker = sys.argv[1]
    
    try:
        # 1. Run the async web scraping
        raw_excel_path = await download_excel_for_stock_async(stock_ticker)
        
        if not raw_excel_path:
            print(f"FAILURE: Web scraping failed for {stock_ticker}.")
            sys.exit(1)

        # 2. Run the synchronous data processing
        # We need to save the processed file with a predictable name.
        processed_file_path = raw_excel_path.parent.parent / "processed" / f"processed_{stock_ticker}.csv"
        
        result = process_and_save_excel(raw_excel_path, specific_save_path=processed_file_path)
        
        if result:
            # Print a success message that is easy for another script to parse
            print(f"SUCCESS:{processed_file_path}")
            sys.exit(0)
        else:
            print(f"FAILURE: Excel processing failed for {raw_excel_path.name}.")
            sys.exit(1)
            
    except Exception as e:
        print(f"FAILURE: An exception occurred during the pipeline: {repr(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # asyncio.run() creates and closes a new event loop, avoiding conflicts.
    asyncio.run(main())