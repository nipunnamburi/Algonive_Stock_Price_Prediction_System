import sys
import os

# Add root directory to python path for local and vercel execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force Keras/TensorFlow to load first to prevent macOS vecLib/OpenMP thread deadlock
from utils.predictor import (
    get_model_and_scaler,
    predict_next_day,
    generate_multistep_forecast,
    calculate_evaluation_metrics,
    get_test_predictions
)

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from utils.data_loader import (
    load_historical_data,
    load_company_info,
    get_available_local_scrips,
    get_available_local_indices,
    get_local_file_path,
    get_local_date_range
)
from utils.preprocessing import calculate_technical_indicators

app = FastAPI(title="Stock Price Prediction API")

# Enable CORS for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DataRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str

class PredictRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    forecast_len: int = 30

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/stocks")
def get_stocks():
    """
    Returns available predefined, local NSE scrips, and index options.
    """
    predefined_companies = {
        "AAPL": "Apple Inc. (US)",
        "GOOG": "Alphabet Inc. (US)",
        "MSFT": "Microsoft Corporation (US)",
        "AMZN": "Amazon.com, Inc. (US)"
    }
    
    local_scrips = get_available_local_scrips()
    local_indices = get_available_local_indices()
    
    return {
        "predefined": predefined_companies,
        "local_scrips": local_scrips,
        "local_indices": local_indices
    }

@app.get("/api/stock-range")
def get_stock_range(ticker: str):
    """
    Returns the date range bounds for a ticker.
    """
    local_path = get_local_file_path(ticker)
    is_local = local_path is not None
    
    if is_local:
        min_dt, max_dt = get_local_date_range(ticker)
        return {
            "is_local": True,
            "min_date": min_dt.strftime("%Y-%m-%d"),
            "max_date": max_dt.strftime("%Y-%m-%d"),
            "default_start": max(min_dt, max_dt - timedelta(days=3*365)).strftime("%Y-%m-%d")
        }
    else:
        end = datetime.now()
        start = datetime(end.year - 5, end.month, end.day)
        return {
            "is_local": False,
            "min_date": "1900-01-01",
            "max_date": end.strftime("%Y-%m-%d"),
            "default_start": start.strftime("%Y-%m-%d")
        }

@app.post("/api/historical")
def get_historical(req: DataRequest):
    """
    Loads historical data, calculates indicators, and returns JSON-formatted data.
    """
    try:
        start_dt = datetime.strptime(req.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    hist_data = load_historical_data(req.ticker, start_dt, end_dt)
    
    if hist_data.empty:
        raise HTTPException(status_code=404, detail=f"No stock data found for ticker '{req.ticker}'.")
        
    company_info = load_company_info(req.ticker)
    processed = calculate_technical_indicators(hist_data)
    
    # Fill NaNs for JSON serialization
    processed = processed.fillna(0.0)
    
    # Format data for charts: list of dicts with date
    records = []
    for idx, row in processed.iterrows():
        records.append({
            "date": idx.strftime("%Y-%m-%d"),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": float(row["Volume"]),
            "sma20": float(row.get("SMA_20", 0.0)),
            "sma50": float(row.get("SMA_50", 0.0)),
            "ema20": float(row.get("EMA_20", 0.0)),
            "rsi14": float(row.get("RSI_14", 0.0))
        })
        
    return {
        "company_info": company_info,
        "historical_data": records
    }

@app.post("/api/predict")
def predict_stock(req: PredictRequest):
    """
    Executes prediction logic and multi-step forecast.
    """
    try:
        start_dt = datetime.strptime(req.start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(req.end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    hist_data = load_historical_data(req.ticker, start_dt, end_dt)
    
    if hist_data.empty:
        raise HTTPException(status_code=404, detail=f"No stock data found for ticker '{req.ticker}'.")
        
    processed = calculate_technical_indicators(hist_data)
    close_prices = processed["Close"].values
    
    if len(close_prices) < 60:
        raise HTTPException(
            status_code=400, 
            detail=f"Selected date range contains only {len(close_prices)} days of data. The LSTM model requires at least 60 days of historical data to predict."
        )
        
    try:
        model, scaler = get_model_and_scaler(req.ticker, close_prices)
        last_60 = close_prices[-60:]
        
        # Predict tomorrow
        tomorrow_pred, growth = predict_next_day(model, scaler, last_60)
        
        # Multi-step forecast
        forecast = generate_multistep_forecast(model, scaler, last_60, req.forecast_len)
        
        # Evaluate model on test slice (last 5% of data)
        dataset = close_prices.reshape(-1, 1)
        training_data_len = int(np.ceil(len(dataset) * 0.95))
        
        y_test, predictions = get_test_predictions(model, scaler, dataset, training_data_len)
        rmse, mae, mape, accuracy = calculate_evaluation_metrics(y_test, predictions)
        
        # Format forecast response
        last_date = processed.index[-1]
        forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=req.forecast_len, freq='B')
        
        forecast_records = []
        for i, val in enumerate(forecast):
            forecast_records.append({
                "day": i + 1,
                "date": forecast_dates[i].strftime("%Y-%m-%d"),
                "prediction": float(val)
            })
            
        return {
            "tomorrow_prediction": float(tomorrow_pred),
            "expected_growth_pct": float(growth),
            "metrics": {
                "available": len(y_test) > 0 and len(predictions) > 0,
                "rmse": float(rmse),
                "mae": float(mae),
                "mape": float(mape),
                "accuracy": float(accuracy)
            },
            "forecast": forecast_records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model execution error: {str(e)}")
