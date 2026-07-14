import os
import numpy as np
import onnxruntime as ort
import pandas as pd
import joblib
from sklearn.preprocessing import MinMaxScaler
from typing import Tuple, List

# Define directories
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(base_dir, 'models')
MODEL_PATH = os.path.join(MODELS_DIR, 'lstm_model.onnx')
SCALER_PATH = os.path.join(MODELS_DIR, 'scaler.pkl')

def get_model_and_scaler(symbol: str, close_prices: np.ndarray) -> Tuple[ort.InferenceSession, MinMaxScaler]:
    """
    Loads the trained LSTM model (ONNX session) and returns the appropriate scaler.
    If the stock is AAPL, loads the pre-fitted scaler.
    Otherwise, fits a new MinMaxScaler on the stock's historical close prices.
    """
    # Load model ONNX session (forced on CPU)
    session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
    
    if symbol.upper() == 'AAPL' and os.path.exists(SCALER_PATH):
        scaler = joblib.load(SCALER_PATH)
    else:
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaler.fit(close_prices.reshape(-1, 1))
        
    return session, scaler

def run_inference(session: ort.InferenceSession, x_input: np.ndarray) -> np.ndarray:
    """
    Runs inference using the ONNX model session.
    """
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    x_input_f32 = x_input.astype(np.float32)
    return session.run([output_name], {input_name: x_input_f32})[0]

def predict_next_day(model: ort.InferenceSession, scaler, last_60_days: np.ndarray) -> Tuple[float, float]:
    """
    Predicts the stock price for the next trading day.
    Returns: (predicted_price, expected_growth_pct)
    """
    # Scale input
    scaled_input = scaler.transform(last_60_days.reshape(-1, 1))
    
    # Reshape for LSTM: (batch_size, timesteps, features) -> (1, 60, 1)
    x_input = np.reshape(scaled_input, (1, len(scaled_input), 1))
    
    # Predict using ONNX
    predicted_scaled = run_inference(model, x_input)
    
    # Inverse scale
    predicted_price = float(scaler.inverse_transform(predicted_scaled)[0, 0])
    
    # Calculate expected growth relative to last closing price
    last_price = float(last_60_days[-1])
    growth_pct = ((predicted_price - last_price) / last_price) * 100
    
    return predicted_price, growth_pct

def generate_multistep_forecast(model: ort.InferenceSession, scaler, last_60_days: np.ndarray, forecast_days: int) -> List[float]:
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
        
        # Predict next scaled price using ONNX
        pred_scaled = run_inference(model, x_input)[0, 0]
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
    if len(y_true) == 0 or len(y_pred) == 0:
        return 0.0, 0.0, 0.0, 0.0
        
    y_true = y_true.flatten()
    y_pred = y_pred.flatten()
    
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae = float(np.mean(np.abs(y_true - y_pred)))
    
    # MAPE (avoiding division by zero)
    mape = float(np.mean(np.abs((y_true - y_pred) / (y_true + 1e-10))) * 100)
    
    # Accuracy representation as 100 - MAPE (clamped to 0-100)
    accuracy = max(0.0, 100.0 - mape)
    
    return rmse, mae, mape, accuracy

def get_test_predictions(model: ort.InferenceSession, scaler, dataset: np.ndarray, training_data_len: int) -> Tuple[np.ndarray, np.ndarray]:
    """
    Recreates the test slice predictions to evaluate performance metrics.
    """
    if len(dataset) < 61:
        return np.array([]), np.array([])
        
    if training_data_len >= len(dataset):
        training_data_len = len(dataset) - 1
        
    start_idx = training_data_len - 60
    if start_idx < 0:
        start_idx = 0
        training_data_len = 60
        
    scaled_data = scaler.transform(dataset)
    test_data = scaled_data[start_idx:, :]
    
    x_test = []
    y_test = dataset[training_data_len:, :]
    for i in range(60, len(test_data)):
        x_test.append(test_data[i-60:i, 0])
        
    x_test = np.array(x_test)
    if len(x_test) == 0:
        return np.array([]), np.array([])
        
    x_test = np.reshape(x_test, (x_test.shape[0], x_test.shape[1], 1))
    
    # Predict using ONNX
    predictions_scaled = run_inference(model, x_test)
    predictions = scaler.inverse_transform(predictions_scaled)
    
    min_len = min(len(y_test), len(predictions))
    return y_test[:min_len], predictions[:min_len]
