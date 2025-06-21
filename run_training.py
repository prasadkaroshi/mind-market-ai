# run_training.py (Complete and Final Version)

import sys
import time
import subprocess
from pathlib import Path
from model_trainer import train_and_save_model
from config import MODELS_DIR, PROCESSED_DATA_DIR

def get_or_update_data_and_model(stock_ticker: str, max_age_hours: int = 24, force_refresh: bool = False):
    """
    Manages data and model files. When a refresh is needed, it calls the
    standalone pipeline script to avoid asyncio conflicts.
    """
    stock_ticker = stock_ticker.upper()
    model_path = MODELS_DIR / f"{stock_ticker}_model.joblib"
    data_path_to_use = None

    should_refresh = False
    if force_refresh:
        should_refresh = True
    elif not model_path.exists():
        should_refresh = True
    else:
        age_in_hours = (time.time() - model_path.stat().st_mtime) / 3600
        if age_in_hours > max_age_hours:
            should_refresh = True

    if should_refresh:
        print(f"--- Refreshing data for {stock_ticker} by calling standalone pipeline ---")
        
        command = [sys.executable, "run_pipeline_standalone.py", stock_ticker]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8')

        # --- THIS IS THE CORRECTED LOGIC ---
        # We check if the SUCCESS message is ANYWHERE in the output, and that the exit code was 0.
        if result.returncode == 0 and "SUCCESS:" in result.stdout:
            # Find the line with the success message and extract the path
            success_line = [line for line in result.stdout.splitlines() if line.startswith("SUCCESS:")][0]
            processed_csv_path_str = success_line.split(":", 1)[1]
            processed_csv_path = Path(processed_csv_path_str)
            print(f"Pipeline script successful. Data at: {processed_csv_path}")
        else:
            # If the script failed, raise a detailed error
            error_message = f"Standalone pipeline script failed for {stock_ticker}.\n"
            error_message += f"Exit Code: {result.returncode}\n"
            error_message += f"Stdout: {result.stdout.strip()}\n"
            error_message += f"Stderr: {result.stderr.strip()}"
            raise RuntimeError(error_message)
        
        train_and_save_model(processed_csv_path, model_path)
        print(f"✅ Successfully created/updated model: {model_path}")
        data_path_to_use = processed_csv_path
        
    else:
        print(f"Using cached model for {stock_ticker}.")
        try:
            list_of_files = list(PROCESSED_DATA_DIR.glob('processed_*.csv'))
            if not list_of_files:
                print("Model found, but no data files exist. Forcing a refresh.")
                return get_or_update_data_and_model(stock_ticker, force_refresh=True)
            data_path_to_use = max(list_of_files, key=lambda p: p.stat().st_mtime)
        except Exception as e:
            raise FileNotFoundError(f"Could not find a suitable data file for cached model. Error: {e}")

    if not data_path_to_use or not data_path_to_use.exists():
        raise FileNotFoundError(f"Could not find or determine a data file for {stock_ticker}.")

    return model_path, data_path_to_use

# Keep main block for manual training
if __name__ == "__main__":
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        get_or_update_data_and_model(ticker, force_refresh=True)
    else:
        print("Usage: python run_training.py <STOCK_TICKER>")