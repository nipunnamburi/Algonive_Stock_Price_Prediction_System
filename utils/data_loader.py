import yfinance as yf
import pandas as pd
from datetime import datetime

def load_historical_data(ticker_symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Downloads historical stock data for a given ticker and date range.
    """
    try:
        df = yf.download(ticker_symbol, start=start_date, end=end_date, auto_adjust=False, threads=False)
        if df.empty:
            return pd.DataFrame()
        
        # Clean columns if multi-indexed
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        return df
    except Exception as e:
        print(f"Error loading historical data for {ticker_symbol}: {e}")
        return pd.DataFrame()

def load_company_info(ticker_symbol: str) -> dict:
    """
    Fetches company metadata (Name, Sector, Exchange, Market Cap, PE Ratio) using yfinance Ticker.
    """
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # Extract fields with safe fallbacks
        metadata = {
            "name": info.get("longName", info.get("shortName", ticker_symbol)),
            "sector": info.get("sector", "N/A"),
            "exchange": info.get("exchange", "N/A"),
            "market_cap": info.get("marketCap", None),
            "pe_ratio": info.get("trailingPE", info.get("forwardPE", None)),
            "current_price": info.get("currentPrice", info.get("regularMarketPrice", None)),
            "currency": info.get("currency", "USD"),
            "symbol": ticker_symbol.upper()
        }
        return metadata
    except Exception as e:
        print(f"Error loading company info for {ticker_symbol}: {e}")
        return {
            "name": ticker_symbol.upper(),
            "sector": "N/A",
            "exchange": "N/A",
            "market_cap": None,
            "pe_ratio": None,
            "current_price": None,
            "currency": "USD",
            "symbol": ticker_symbol.upper()
        }
