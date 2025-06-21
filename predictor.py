# predictor.py

import pandas as pd
import joblib
from pathlib import Path
from typing import Tuple, Any
from model_trainer import preprocess_for_training # Reuse the same preprocessing logic

def format_prediction(value: float) -> str:
    """Formats the prediction value into a human-readable currency string (in Crores)."""
    if value is None:
        return "N/A"
    return f"₹ {value:,.2f} Cr"

def make_prediction(model: Any, latest_data: pd.DataFrame) -> Tuple[str, float]:
    """
    Uses a trained model to predict the next quarter's sales.

    Args:
        model (Any): The loaded scikit-learn model object.
        latest_data (pd.DataFrame): The most recent processed data for the stock.

    Returns:
        Tuple[str, float]: A tuple containing the formatted prediction string
                           and a placeholder confidence score.
    """
    print("--- Making a new prediction ---")
    
    try:
        # Preprocess the data into the same format used for training
        processed_df = preprocess_for_training(latest_data)
        
        if processed_df is None or processed_df.empty:
            raise ValueError("Not enough data to make a prediction after preprocessing.")
            
        # Get the last row of historical data to use as input
        last_known_data = processed_df.iloc[-1]
        
        # Prepare the features for the next time step:
        # The 'Sales' from the last known period becomes the 'Sales_Lag1' for the new prediction.
        # The 'Time_Step' is incremented by 1.
        next_timestep_features = {
            'Sales_Lag1': [last_known_data['Sales']],
            'Time_Step': [last_known_data['Time_Step'] + 1]
        }
        
        X_new = pd.DataFrame(next_timestep_features)
        
        predicted_sales = model.predict(X_new)[0]
        
        formatted_prediction = format_prediction(predicted_sales)
        
        # NOTE: Confidence score is a placeholder. A more complex model (e.g., ARIMA)
        # would provide a true confidence interval. We use a static value for this model.
        confidence = 0.75
        
        print(f"Prediction successful: {formatted_prediction}")
        return formatted_prediction, confidence

    except (ValueError, IndexError) as e:
        print(f"Prediction failed due to data issue: {e}")
        return "Data Insufficient", 0.0
    except Exception as e:
        print(f"An unexpected error occurred during prediction: {e}")
        return "Prediction Error", 0.0

# This block allows direct testing of the prediction process
if __name__ == '__main__':
    from config import PROCESSED_DATA_DIR, MODELS_DIR
    
    print("--- Running predictor.py directly for testing ---")
    try:
        # Find the latest model and data file
        latest_model_path = max(MODELS_DIR.glob('*.joblib'), key=lambda p: p.stat().st_mtime)
        model_ticker = latest_model_path.stem.split('_model')[0]
        latest_data_path = PROCESSED_DATA_DIR / f"processed_{model_ticker}.csv"
        
        print(f"Found latest model for testing: {latest_model_path.name}")
        print(f"Using corresponding data file: {latest_data_path.name}")

        if not latest_data_path.exists():
            raise FileNotFoundError(f"Data file {latest_data_path.name} not found.")

        # Load the model and data
        loaded_model = joblib.load(latest_model_path)
        data_df = pd.read_csv(latest_data_path, index_col=0)

        # Run the prediction
        prediction, confidence = make_prediction(loaded_model, data_df)
        
        print("\n--- TEST PREDICTION RESULT ---")
        print(f"Predicted Next Quarter Sales: {prediction}")
        print(f"Confidence: {confidence:.0%}")

    except ValueError:
        print("No model or data files found in 'models' or 'data/processed'.")
        print("Please run 'python run_training.py <TICKER>' first.")
    except Exception as e:
        print(f"An error occurred during the test run: {e}")