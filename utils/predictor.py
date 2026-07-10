import os
import numpy as np
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler
from keras.models import load_model
from typing import Tuple, List

# Define directories
MODELS_DIR = '/Users/nipunnamburi/Downloads/Algonive Internship/StockPricePredictionSystem/models'
MODEL_PATH = os.path.join(MODELS_DIR, 'lstm_model.keras')
SCALER_PATH = os.path.join(MODELS_DIR, 'scaler.pkl')

def get_model_and_scaler(symbol: str, close_prices: np.ndarray) -> Tuple[any, MinMaxScaler]:
    """
    Loads the trained LSTM model and returns the appropriate scaler.
    If the stock is AAPL, loads the pre-fitted scaler.
    Otherwise, fits a new MinMaxScaler on the stock's historical close prices.
    """
    # Load model (forced on CPU)
    model = load_model(MODEL_PATH)
    
    if symbol.upper() == 'AAPL' and os.path.exists(SCALER_PATH):
        scaler = joblib.load(SCALER_PATH)
    else:
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(close_prices.reshape(-1, 1))
        
    return model, scaler

def predict_next_day(model, scaler, last_60_days: np.ndarray) -> Tuple[float, float]:
    """
    Predicts the stock price for the next trading day.
    Returns: (predicted_price, expected_growth_pct)
    """
    # Scale input
    scaled_input = scaler.transform(last_60_days.reshape(-1, 1))
    
    # Reshape for LSTM: (batch_size, timesteps, features) -> (1, 60, 1)
    x_input = np.reshape(scaled_input, (1, len(scaled_input), 1))
    
    # Predict
    predicted_scaled = model.predict(x_input, verbose=0)
    
    # Inverse scale
    predicted_price = float(scaler.inverse_transform(predicted_scaled)[0, 0])
    
    # Calculate expected growth relative to last closing price
    last_price = float(last_60_days[-1])
    growth_pct = ((predicted_price - last_price) / last_price) * 100
    
    return predicted_price, growth_pct

def generate_multistep_forecast(model, scaler, last_60_days: np.ndarray, forecast_days: int) -> List[float]:
    """
    Generates a multi-step autoregressive forecast for N days using the LSTM.
    """
    # Copy and scale current sequence
    current_sequence = list(scaler.transform(last_60_days.reshape(-1, 1)).flatten())
    predictions_scaled = []
    
    for _ in range(forecast_days):
        # Prepare input of the last 60 days
        x_input = np.array(current_sequence[-60:])
        x_input = np.reshape(x_input, (1, 60, 1))
        
        # Predict next scaled price
        pred_scaled = model.predict(x_input, verbose=0)[0, 0]
        predictions_scaled.append(pred_scaled)
        
        # Append to sequence
        current_sequence.append(pred_scaled)
        
    # Inverse scale predictions
    predictions_scaled_arr = np.array(predictions_scaled).reshape(-1, 1)
    predictions = scaler.inverse_transform(predictions_scaled_arr).flatten().tolist()
    
    return predictions

def calculate_evaluation_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Tuple[float, float, float, float]:
    """
    Calculates regression evaluation metrics: RMSE, MAE, MAPE, and Accuracy.
    """
    y_true = y_true.flatten()
    y_pred = y_pred.flatten()
    
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    
    # MAPE (avoiding division by zero)
    mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100)
    
    # Accuracy representation as 100 - MAPE (clamped to 0-100)
    accuracy = max(0.0, 100.0 - mape)
    
    return rmse, mae, mape, accuracy

def get_test_predictions(model, scaler, dataset: np.ndarray, training_data_len: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Recreates the test slice predictions to evaluate performance metrics.
    """
    scaled_data = scaler.transform(dataset)
    test_data = scaled_data[training_data_len - 60:, :]
    
    x_test = []
    y_test = dataset[training_data_len:, :]
    for i in range(60, len(test_data)):
        x_test.append(test_data[i-60:i, 0])
        
    x_test = np.array(x_test)
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
    
    predictions_scaled = model.predict(x_test, verbose=0)
    predictions = scaler.inverse_transform(predictions_scaled)
    
    return y_test, predictions
