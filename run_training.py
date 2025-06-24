# run_training.py (Full, Final, and Corrected for SCREENER_USERNAME)

import sys
import time
import subprocess
from pathlib import Path
from model_trainer import train_and_save_model
from config import MODELS_DIR, PROCESSED_DATA_DIR

import os
import toml 

def get_or_update_data_and_model(stock_ticker: str, max_age_hours: int = 24, force_refresh: bool = False):
    """
    Manages data and model files. When a refresh is needed, it calls the
    standalone pipeline script, passing secrets securely to its environment.
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
        
        try:
            secrets_path = Path(".streamlit/secrets.toml")
            if not secrets_path.exists():
                raise FileNotFoundError("CRITICAL: Could not find the secrets file at .streamlit/secrets.toml")
            
            secrets = toml.load(secrets_path)
            screener_username = secrets.get("SCREENER_USERNAME")
            screener_password = secrets.get("SCREENER_PASSWORD")

            if not screener_username or not screener_password:
                raise ValueError("CRITICAL: SCREENER_USERNAME or SCREENER_PASSWORD not found inside your secrets.toml file.")

        except Exception as e:
            print(f"FATAL ERROR: Failed to load credentials. Please check your .streamlit/secrets.toml file.")
            print(f"Details: {e}")
            sys.exit(1)

        env = os.environ.copy()
        # The backend script expects SCREENER_EMAIL, so we map our username to it.
        env["SCREENER_EMAIL"] = screener_username 
        env["SCREENER_PASSWORD"] = screener_password
        
        command = [sys.executable, "run_pipeline_standalone.py", stock_ticker]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', env=env)

        if result.returncode == 0 and "SUCCESS:" in result.stdout:
            success_line = [line for line in result.stdout.splitlines() if line.startswith("SUCCESS:")][0]
            processed_csv_path_str = success_line.split(":", 1)[1]
            processed_csv_path = Path(processed_csv_path_str)
            print(f"Pipeline script successful. Data at: {processed_csv_path}")
        else:
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
            data_path_to_use = PROCESSED_DATA_DIR / f"processed_{stock_ticker}.csv"
            if not data_path_to_use.exists():
                 raise FileNotFoundError
        except FileNotFoundError:
            print(f"Model for {stock_ticker} found, but corresponding data file is missing. Forcing a refresh.")
            return get_or_update_data_and_model(stock_ticker, force_refresh=True)

    if not data_path_to_use or not data_path_to_use.exists():
        raise FileNotFoundError(f"Could not find or determine a data file for {stock_ticker}.")

    return model_path, data_path_to_use

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        get_or_update_data_and_model(ticker, force_refresh=True)
    else:
        print("Usage: python run_training.py <STOCK_TICKER>")