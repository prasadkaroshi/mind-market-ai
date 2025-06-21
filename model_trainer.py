# model_trainer.py

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib
from pathlib import Path
from typing import Optional

def preprocess_for_training(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """
    Prepares data for sales forecasting by extracting and transforming the 'Sales' row.

    Args:
        df (pd.DataFrame): The processed DataFrame from the excel_processor.

    Returns:
        Optional[pd.DataFrame]: A DataFrame formatted for time-series training, or None if failed.
    """
    # Find the 'Sales' row, case-insensitively
    sales_row_name = next((idx for idx in df.index if 'sales' in str(idx).lower()), None)
    
    if not sales_row_name:
        raise ValueError("'Sales' data not found in the provided DataFrame.")

    sales_data = df.loc[sales_row_name].dropna()
    
    if sales_data.empty or len(sales_data) < 2:
        raise ValueError("Sales data is empty or has insufficient points after dropping NaNs.")
        
    # Convert to a DataFrame suitable for scikit-learn
    sales_df = sales_data.to_frame(name='Sales')
    
    # Create features for time-series forecasting:
    # 1. Lagged Sales (previous period's sales)
    sales_df['Sales_Lag1'] = sales_df['Sales'].shift(1)
    # 2. Time Step (a simple counter to model the trend)
    sales_df['Time_Step'] = range(len(sales_df))
    
    # Drop rows with NaN values created by the shift() operation
    sales_df.dropna(inplace=True)
    
    return sales_df

def train_and_save_model(data_path: Path, model_save_path: Path) -> None:
    """
    Loads processed data, trains a simple sales forecasting model, and saves it.
    
    Args:
        data_path (Path): Path to the processed CSV data file.
        model_save_path (Path): Path where the trained model should be saved.
    """
    print(f"--- Starting model training from: {data_path.name} ---")
    
    try:
        df = pd.read_csv(data_path, index_col=0)
        
        training_df = preprocess_for_training(df)
        
        if training_df is None or len(training_df) < 2:
            raise ValueError("Not enough data points to train the model (need at least 2).")

        # Define features (X) and target (y)
        # We use previous sales and a time counter to predict current sales.
        X = training_df[['Sales_Lag1', 'Time_Step']]
        y = training_df['Sales']
        
        # Train a simple Linear Regression model
        model = LinearRegression()
        model.fit(X, y)
        
        print("Model training completed successfully.")
        
        # Save the trained model
        joblib.dump(model, model_save_path)
        print(f"Model saved to: {model_save_path}")

    except FileNotFoundError:
        print(f"Error: Data file not found at {data_path}")
        raise
    except ValueError as ve:
        print(f"Data processing or training error: {ve}")
        raise
    except Exception as e:
        print(f"An unexpected error occurred during model training: {e}")
        raise

# This block allows direct testing of the training process
if __name__ == '__main__':
    from config import PROCESSED_DATA_DIR, MODELS_DIR
    
    print("--- Running model_trainer.py directly for testing ---")
    try:
        # Find the latest processed file to use for the test run
        latest_file = max(PROCESSED_DATA_DIR.glob('processed_*.csv'), key=lambda p: p.stat().st_mtime)
        print(f"Found latest data file for testing: {latest_file.name}")
        
        # Define where to save the test model
        file_stem = latest_file.stem.replace('processed_', '')
        test_model_path = MODELS_DIR / f"{file_stem}_test_model.joblib"
        
        train_and_save_model(latest_file, test_model_path)
        
    except ValueError:
        print("No processed data files found in 'data/processed' to run a test.")
        print("Please run 'python main.py <TICKER>' first.")
    except Exception as e:
        print(f"An error occurred during the test run: {e}")