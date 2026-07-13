import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from utils.data_loader import (
    load_historical_data,
    load_company_info,
    get_available_local_scrips,
    get_available_local_indices,
    get_local_file_path,
    get_local_date_range
)
from utils.preprocessing import calculate_technical_indicators
from utils.predictor import (
    get_model_and_scaler,
    predict_next_day,
    generate_multistep_forecast,
    calculate_evaluation_metrics,
    get_test_predictions
)
from utils.visualization import plot_historical_prices, plot_volume, plot_forecast

# App configurations
st.set_page_config(
    page_title="Stock Price Prediction System",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for rich aesthetics and responsive UI
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222b;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        margin-bottom: 15px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #00ffcc;
    }
    .metric-label {
        font-size: 14px;
        color: #8a8e97;
    }
</style>
""", unsafe_allow_html=True)

# Cache model load to speed up app loading
@st.cache_resource
def load_trained_model(symbol: str, close_prices: np.ndarray):
    return get_model_and_scaler(symbol, close_prices)

# Header
st.title("📈 Stock Price Prediction System")
st.markdown("---")

# Sidebar for controls
st.sidebar.header("🔍 Search Stock")

# Predefined companies mapping
predefined_companies = {
    "AAPL": "Apple Inc. (US)",
    "GOOG": "Alphabet Inc. (US)",
    "MSFT": "Microsoft Corporation (US)",
    "AMZN": "Amazon.com, Inc. (US)"
}

# Fetch lists of local scrips and indices
local_scrips = get_available_local_scrips()
local_indices = get_available_local_indices()

# Stock select dropdown or custom ticker
selection_mode = st.sidebar.radio(
    "Select input mode:", 
    [
        "Predefined US Stocks", 
        "Local NSE Scrips (Datasets)", 
        "Local NSE Indices (Datasets)", 
        "Local S&P 500 Index (Datasets)", 
        "Search Custom Ticker (Online)"
    ]
)

ticker_input = ""
if selection_mode == "Predefined US Stocks":
    selected_name = st.sidebar.selectbox("Choose Company:", list(predefined_companies.values()))
    ticker_input = [k for k, v in predefined_companies.items() if v == selected_name][0]
elif selection_mode == "Local NSE Scrips (Datasets)":
    if local_scrips:
        selected_display = st.sidebar.selectbox("Choose NSE Scrip:", list(local_scrips.values()))
        ticker_input = [k for k, v in local_scrips.items() if v == selected_display][0]
    else:
        st.sidebar.warning("No local NSE scrips found in Datasets/SCRIP.")
elif selection_mode == "Local NSE Indices (Datasets)":
    if local_indices:
        ticker_input = st.sidebar.selectbox("Choose NSE Index:", local_indices)
    else:
        st.sidebar.warning("No local NSE indices found in Datasets/INDEX.")
elif selection_mode == "Local S&P 500 Index (Datasets)":
    ticker_input = "SPX"
else:
    ticker_input = st.sidebar.text_input("Enter Ticker Symbol (e.g. TSLA, NVDA):", value="AAPL").strip().upper()

# Date range selection for historical data
st.sidebar.subheader("📅 Date Range")

is_local = get_local_file_path(ticker_input) is not None

if is_local:
    min_date, max_date = get_local_date_range(ticker_input)
    # Default to last 3 years of the dataset (or min_date if dataset is smaller)
    default_start = max(min_date, max_date - timedelta(days=3*365))
    
    start_date = st.sidebar.date_input("Start Date:", value=default_start, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date:", value=max_date, min_value=min_date, max_value=max_date)
    
    # Convert date to datetime
    start_date = datetime.combine(start_date, datetime.min.time())
    end_date = datetime.combine(end_date, datetime.max.time())
else:
    end_date_now = datetime.now()
    start_date_now = datetime(end_date_now.year - 5, end_date_now.month, end_date_now.day)
    
    start_date = st.sidebar.date_input("Start Date:", value=start_date_now, max_value=end_date_now)
    end_date = st.sidebar.date_input("End Date:", value=end_date_now, max_value=end_date_now)
    
    start_date = datetime.combine(start_date, datetime.min.time())
    end_date = datetime.combine(end_date, datetime.max.time())

# Action buttons
predict_clicked = st.sidebar.button("Predict Stock Price", type="primary")

# Formatting helpers
def format_large_number(num, symbol="$"):
    if num is None:
        return "N/A"
    if num >= 1e12:
        return f"{symbol}{num / 1e12:.2f}T"
    elif num >= 1e9:
        return f"{symbol}{num / 1e9:.2f}B"
    elif num >= 1e6:
        return f"{symbol}{num / 1e6:.2f}M"
    return f"{symbol}{num:,.2f}"

def format_volume(num):
    if num is None:
        return "N/A"
    if num >= 1e6:
        return f"{num / 1e6:.1f}M"
    elif num >= 1e3:
        return f"{num / 1e3:.1f}K"
    return str(num)

# Load data
if ticker_input:
    with st.spinner(f"Loading data for {ticker_input}..."):
        hist_data = load_historical_data(ticker_input, start_date, end_date)
        company_info = load_company_info(ticker_input)

    if hist_data.empty:
        st.error(f"Failed to fetch stock data for ticker '{ticker_input}'. Please check the symbol and try again.")
    else:
        # Determine currency symbol
        currency_symbol = "₹" if company_info.get("currency") == "INR" else "$"
        
        # Calculate technical indicators
        processed_data = calculate_technical_indicators(hist_data)
        
        # Display Company Metadata
        st.subheader(f"🏢 Company Info: {company_info['name']} ({company_info['symbol']})")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Stats Calculations
        last_row = processed_data.iloc[-1]
        highest_52w = float(processed_data['High'].tail(252).max())
        lowest_52w = float(processed_data['Low'].tail(252).min())
        
        with col1:
            st.metric(
                label="Current Price",
                value=f"{currency_symbol}{last_row['Close']:.2f}",
                delta=f"{last_row['Close'] - processed_data['Close'].iloc[-2]:.2f} (Daily)"
            )
        with col2:
            st.metric(label="52-Week High", value=f"{currency_symbol}{highest_52w:.2f}")
        with col3:
            st.metric(label="52-Week Low", value=f"{currency_symbol}{lowest_52w:.2f}")
        with col4:
            st.metric(label="Daily Volume", value=format_volume(last_row['Volume']))
        with col5:
            st.metric(label="Market Cap", value=format_large_number(company_info['market_cap'], currency_symbol))
            
        # Sector and Info
        st.markdown(f"**Sector:** {company_info['sector']} | **Exchange:** {company_info['exchange']} | **P/E Ratio:** {company_info['pe_ratio'] if company_info['pe_ratio'] else 'N/A'}")
        
        # Generalization Note if not Apple
        if ticker_input != "AAPL":
            st.info(
                "💡 **Model Generalization Note:** The core LSTM model was trained on historical Apple (AAPL) data. "
                "For this ticker, the system automatically scaled the prices using a local MinMaxScaler fitted on "
                f"historical {ticker_input} data to generate correctly scaled predictions. Actual accuracy may vary."
            )
            
        st.markdown("---")
        
        # Historical Analysis Section
        st.subheader("📊 Historical Analysis")
        chart_col, table_col = st.columns([3, 1])
        
        with chart_col:
            st.plotly_chart(plot_historical_prices(processed_data, ticker_input, currency_symbol), use_container_width=True)
            st.plotly_chart(plot_volume(processed_data, ticker_input), use_container_width=True)
            
        with table_col:
            st.markdown("#### Technical Indicators")
            st.write(processed_data[['Close', 'SMA_20', 'SMA_50', 'EMA_20', 'RSI_14']].tail(10))
            
            # Indicators Card
            st.markdown("##### Technical Summary")
            st.markdown(f"""
            - **Current SMA 20:** {currency_symbol}{last_row['SMA_20']:.2f}
            - **Current SMA 50:** {currency_symbol}{last_row['SMA_50']:.2f}
            - **Current EMA 20:** {currency_symbol}{last_row['EMA_20']:.2f}
            - **Current RSI 14:** {last_row['RSI_14']:.2f}
            """)
            if last_row['RSI_14'] > 70:
                st.warning("⚠️ RSI indicates Overbought (> 70)")
            elif last_row['RSI_14'] < 30:
                st.success("🟢 RSI indicates Oversold (< 30)")
            else:
                st.info("ℹ️ RSI indicates Neutral range (30-70)")
                
        st.markdown("---")
        
        # ML Predictions Block
        if predict_clicked:
            st.subheader("🔮 Machine Learning Predictions & Forecast")
            
            close_prices = processed_data['Close'].values
            
            if len(close_prices) < 60:
                st.error(f"Error: Selected stock range only contains {len(close_prices)} days of data. The LSTM model requires at least 60 days of historical data to predict.")
            else:
                # Run prediction logic
                with st.spinner("Executing LSTM model predictions..."):
                    # Get model and scaler
                    model, scaler = load_trained_model(ticker_input, close_prices)
                    
                    # Fetch last 60 days
                    last_60_days = close_prices[-60:]
                    
                    # Predict next day
                    tomorrow_pred, growth = predict_next_day(model, scaler, last_60_days)
                    
                    # Forecast options: 7, 30, 90 Days
                    forecast_len = st.selectbox("Select Forecast Horizon:", [7, 30, 90], index=1)
                    forecast = generate_multistep_forecast(model, scaler, last_60_days, forecast_len)
                    
                    # Calculate metrics on Test dataset
                    dataset = close_prices.reshape(-1, 1)
                    training_data_len = int(np.ceil(len(dataset) * 0.95))
                    
                    y_test, predictions = get_test_predictions(model, scaler, dataset, training_data_len)
                    rmse, mae, mape, accuracy = calculate_evaluation_metrics(y_test, predictions)
                    
                # Layout predictions
                pred_col1, pred_col2, pred_col3 = st.columns(3)
                
                with pred_col1:
                    st.metric(
                        label="Tomorrow's Prediction",
                        value=f"{currency_symbol}{tomorrow_pred:.2f}",
                        delta=f"{growth:+.2f}% Expected Change",
                        delta_color="normal"
                    )
                    
                with pred_col2:
                    if len(y_test) > 0 and len(predictions) > 0:
                        # Prediction Metrics Card
                        st.markdown("""
                        <div class="metric-card">
                            <div class="metric-label">Forecast Accuracy</div>
                            <div class="metric-value">{:.2f}%</div>
                            <div class="metric-label">100 - MAPE</div>
                        </div>
                        """.format(accuracy), unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div class="metric-card">
                            <div class="metric-label">Forecast Accuracy</div>
                            <div class="metric-value">N/A</div>
                            <div class="metric-label">Not enough test points</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                with pred_col3:
                    if len(y_test) > 0 and len(predictions) > 0:
                        # Other metrics info
                        st.markdown(f"""
                        **Model Performance Metrics (Test Set)**
                        - **RMSE:** {rmse:.4f}
                        - **MAE:** {mae:.4f}
                        - **MAPE:** {mape:.2f}%
                        """)
                    else:
                        st.markdown("""
                        **Model Performance Metrics (Test Set)**
                        *Not enough historical data points to construct a test set evaluation.*
                        """)
                    
                # Forecast chart and Table layout
                st.markdown("### Multi-Step Forecast Charts & Tables")
                fore_chart_col, fore_table_col = st.columns([3, 1])
                
                with fore_chart_col:
                    # Plotly chart for forecast
                    st.plotly_chart(plot_forecast(processed_data, forecast, ticker_input, currency_symbol), use_container_width=True)
                    
                with fore_table_col:
                    # Display forecast table
                    days = list(range(1, forecast_len + 1))
                    
                    # Generate dates starting from the day after the last historical date
                    last_historical_date = processed_data.index[-1]
                    forecast_dates = pd.date_range(start=last_historical_date + timedelta(days=1), periods=forecast_len, freq='B')
                    
                    forecast_df = pd.DataFrame({
                        "Day": days,
                        "Date": forecast_dates.strftime('%Y-%m-%d'),
                        f"Prediction ({currency_symbol})": [round(p, 2) for p in forecast]
                    })
                    st.dataframe(forecast_df, height=350)
                    
                    # Download CSV button
                    csv = forecast_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Forecast CSV",
                        data=csv,
                        file_name=f"{ticker_input}_forecast_{forecast_len}days.csv",
                        mime="text/csv"
                    )
else:
    st.info("👈 Choose a stock option in the sidebar to get started.")
