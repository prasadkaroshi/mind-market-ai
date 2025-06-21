# data_manager.py
import sys
import time
import subprocess
import os
from pathlib import Path
from config import PROCESSED_DATA_DIR

def get_or_update_data(stock_ticker: str, screener_email: str, screener_password: str, max_age_hours: int = 24, force_refresh: bool = False) -> Path:
    """
    Manages data files by calling a separate script for refreshes.
    It passes credentials securely via environment variables.
    """
    stock_ticker = stock_ticker.upper()
    processed_file_path = PROCESSED_DATA_DIR / f"processed_{stock_ticker}.csv"

    should_refresh = False
    if force_refresh:
        should_refresh = True
    elif not processed_file_path.exists():
        should_refresh = True
    else:
        age_in_hours = (time.time() - processed_file_path.stat().st_mtime) / 3600
        if age_in_hours > max_age_hours:
            should_refresh = True

    if should_refresh:
        print(f"--- Refreshing data for {stock_ticker} via standalone process ---")
        
        # Create a copy of the current environment and add secrets to it
        env = os.environ.copy()
        env["SCREENER_EMAIL"] = screener_email
        env["SCREENER_PASSWORD"] = screener_password

        # Call the isolated script with the enhanced environment
        command = [sys.executable, "run_pipeline_standalone.py", stock_ticker]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', env=env)

        if result.returncode == 0 and "SUCCESS:" in result.stdout:
            print(f"Standalone script successful for {stock_ticker}.")
            if not processed_file_path.exists():
                raise FileNotFoundError(f"Pipeline reported success but file not found at {processed_file_path}")
            return processed_file_path
        else:
            error_message = f"Data pipeline script failed for {stock_ticker}.\n"
            error_message += f"Exit Code: {result.returncode}\n"
            error_message += f"Stdout: {result.stdout.strip()}\n"
            error_message += f"Stderr: {result.stderr.strip()}"
            raise RuntimeError(error_message)
    else:
        print(f"Using cached data for {stock_ticker} from {processed_file_path.name}")
        return processed_file_path