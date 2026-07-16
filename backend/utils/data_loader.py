import os
import pandas as pd
from datetime import datetime
from typing import Tuple, List, Dict

def load_local_csv(filepath: str) -> pd.DataFrame:
    """
    Robust parser for local dataset CSV files.
    Cleans date formats, numeric columns, and handles standard columns.
    """
    df = pd.read_csv(filepath)
    
    # Standardize column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]
    
    # Find the Date column
    date_col = None
    for col in df.columns:
        if col.lower() == 'date':
            date_col = col
            break
            
    if date_col is None:
        raise ValueError(f"No 'Date' column found in {filepath}")
        
    # Convert Date column to datetime
    df[date_col] = pd.to_datetime(df[date_col].astype(str).str.replace('"', '').str.strip(), errors='coerce')
    # Drop rows where date could not be parsed
    df = df.dropna(subset=[date_col])
    
    df.set_index(date_col, inplace=True)
    df.sort_index(inplace=True)
    
    # Identify standard columns: Open, High, Low, Close, Volume
    col_mapping = {}
    for col in df.columns:
        c_low = col.lower()
        if c_low == 'open':
            col_mapping[col] = 'Open'
        elif c_low == 'high':
            col_mapping[col] = 'High'
        elif c_low == 'low':
            col_mapping[col] = 'Low'
        elif c_low in ('close', 'adj close'):
            if 'Close' not in col_mapping.values() or c_low == 'close':
                col_mapping[col] = 'Close'
        elif c_low == 'volume':
            col_mapping[col] = 'Volume'
            
    # Rename columns
    df = df.rename(columns=col_mapping)
    
    # Keep only standard columns
    standard_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    existing_cols = [c for c in standard_cols if c in df.columns]
    df = df[existing_cols]
    
    # Clean numerical columns (remove commas, quotes, and convert to numeric)
    cleaned_data = {}
    for col in df.columns:
        series_str = df[col].astype(str).str.replace('"', '').str.replace(',', '').str.strip()
        cleaned_data[col] = pd.to_numeric(series_str, errors='coerce')
        
    df = pd.DataFrame(cleaned_data, index=df.index)
            
    # Drop rows where Close is missing
    df = df.dropna(subset=['Close'])
    
    # Handle missing Volume
    if 'Volume' not in df.columns:
        df['Volume'] = 0.0
    else:
        df['Volume'] = df['Volume'].fillna(0.0)
        
    # Ensure remaining columns are present
    for col in ['Open', 'High', 'Low']:
        if col not in df.columns:
            df[col] = df['Close']
            
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

def get_local_company_name(ticker_symbol: str) -> str:
    """
    Gets the company name for a local scrip or index.
    """
    ticker_upper = ticker_symbol.upper()
    
    if ticker_upper in ('SPX', 'S&P 500', 'S&P500'):
        return 'S&P 500 Index'
        
    # Check index files
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_file = os.path.join(base_dir, 'Datasets', 'INDEX', f'{ticker_upper}.csv')
    if os.path.exists(index_file):
        return f'{ticker_upper} Index'
        
    # Check SCRIP files using NSE Symbols.CSV
    nse_symbols_path = os.path.join(base_dir, 'Datasets', 'NSE Symbols.CSV')
    if os.path.exists(nse_symbols_path):
        try:
            df_symbols = pd.read_csv(nse_symbols_path)
            df_symbols.columns = [c.strip() for c in df_symbols.columns]
            row = df_symbols[df_symbols['Scrip'].astype(str).str.upper() == ticker_upper]
            if not row.empty:
                return row.iloc[0]['Company Name'].strip()
        except Exception as e:
            print(f"Error reading NSE Symbols.CSV: {e}")
            
    return ticker_upper

def get_available_local_scrips() -> Dict[str, str]:
    """
    Returns a dict mapping ticker -> formatted display name for all available scrips.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    nse_symbols_path = os.path.join(base_dir, 'Datasets', 'NSE Symbols.CSV')
    scrip_dir = os.path.join(base_dir, 'Datasets', 'SCRIP')
    
    scrips = {}
    if os.path.exists(nse_symbols_path) and os.path.exists(scrip_dir):
        try:
            df = pd.read_csv(nse_symbols_path)
            df.columns = [c.strip() for c in df.columns]
            for _, row in df.iterrows():
                symbol = str(row['Scrip']).strip().upper()
                name = str(row['Company Name']).strip()
                if os.path.exists(os.path.join(scrip_dir, f'{symbol}.csv')):
                    scrips[symbol] = f"{symbol} - {name}"
        except Exception as e:
            print(f"Error loading local scrips: {e}")
            
    # Fallback to files in SCRIP directory
    if not scrips and os.path.exists(scrip_dir):
        for f in os.listdir(scrip_dir):
            if f.endswith('.csv') and f != '.DS_Store':
                symbol = f[:-4].upper()
                scrips[symbol] = f"{symbol} (Local)"
                
    return scrips

def get_available_local_indices() -> List[str]:
    """
    Returns a list of available indices in Datasets/INDEX.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    index_dir = os.path.join(base_dir, 'Datasets', 'INDEX')
    
    indices = []
    if os.path.exists(index_dir):
        for f in os.listdir(index_dir):
            if f.endswith('.csv') and f != '.DS_Store':
                indices.append(f[:-4].upper())
    return sorted(indices)

def get_local_file_path(ticker_symbol: str) -> str:
    """
    Helper to check and return the file path if a ticker is available in local datasets.
    """
    ticker_upper = ticker_symbol.upper()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    datasets_dir = os.path.join(base_dir, 'Datasets')
    
    # 1. S&P 500 Check
    if ticker_upper in ('SPX', 'S&P 500', 'S&P500'):
        sp500_path = os.path.join(datasets_dir, 'sp 500.csv')
        if os.path.exists(sp500_path):
            return sp500_path
            
    # 2. Local Index Check
    index_path = os.path.join(datasets_dir, 'INDEX', f'{ticker_upper}.csv')
    if os.path.exists(index_path):
        return index_path
        
    # 3. Local Scrip Check
    scrip_path = os.path.join(datasets_dir, 'SCRIP', f'{ticker_upper}.csv')
    if os.path.exists(scrip_path):
        return scrip_path
        
    return None

def get_local_date_range(ticker_symbol: str) -> Tuple[datetime, datetime]:
    """
    Returns the min and max dates available in the local dataset for a ticker.
    """
    local_path = get_local_file_path(ticker_symbol)
    if local_path:
        try:
            df = pd.read_csv(local_path, usecols=['Date'])
            df['Date'] = pd.to_datetime(df['Date'].astype(str).str.replace('"', '').str.strip(), errors='coerce')
            df = df.dropna()
            if not df.empty:
                return df['Date'].min().to_pydatetime(), df['Date'].max().to_pydatetime()
        except Exception as e:
            print(f"Error getting local date range for {ticker_symbol}: {e}")
            
    # Fallback
    end = datetime.now()
    start = datetime(end.year - 5, end.month, end.day)
    return start, end

def load_historical_data(ticker_symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """
    Downloads historical stock data for a given ticker and date range.
    Integrates local datasets and falls back to yfinance.
    """
    # Try loading from local datasets first
    local_path = get_local_file_path(ticker_symbol)
    if local_path:
        try:
            df = load_local_csv(local_path)
            # Filter by date
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df = df.loc[start_dt:end_dt]
            return df
        except Exception as e:
            print(f"Error loading local data for {ticker_symbol} from {local_path}: {e}")
            
    # Online fallback
    try:
        import yfinance as yf
        df = yf.download(ticker_symbol, start=start_date, end=end_date, auto_adjust=False, threads=False)
        if df.empty:
            return pd.DataFrame()
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
            
        return df
    except Exception as e:
        print(f"Error loading historical data from yfinance for {ticker_symbol}: {e}")
        return pd.DataFrame()

def load_company_info(ticker_symbol: str) -> dict:
    """
    Fetches company metadata (Name, Sector, Exchange, Market Cap, PE Ratio).
    Checks local datasets first, falls back to yfinance.
    """
    ticker_upper = ticker_symbol.upper()
    local_path = get_local_file_path(ticker_symbol)
    
    if local_path:
        name = get_local_company_name(ticker_symbol)
        
        # Check exchange/sector category
        if 'INDEX' in local_path or ticker_upper in ('SPX', 'S&P 500', 'S&P500'):
            sector = 'Index'
            exchange = 'NSE' if 'INDEX' in local_path else 'NYSE/NASDAQ'
        else:
            sector = 'Public Equity'
            exchange = 'NSE'
            
        return {
            "name": name,
            "sector": sector,
            "exchange": exchange,
            "market_cap": None,
            "pe_ratio": None,
            "current_price": None,
            "currency": "INR" if exchange == 'NSE' else "USD",
            "symbol": ticker_upper
        }
        
    try:
        import yfinance as yf
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
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
        print(f"Error loading company info from yfinance for {ticker_symbol}: {e}")
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
