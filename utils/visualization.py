import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

def plot_historical_prices(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Creates an interactive line chart showing close prices, SMA 20, SMA 50, and EMA 20.
    """
    fig = go.Figure()
    
    # Historical Close
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'],
        name='Close Price',
        line=dict(color='#1f77b4', width=2.5)
    ))
    
    # SMA 20
    if 'SMA_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA_20'],
            name='SMA 20',
            line=dict(color='#ff7f0e', width=1.5, dash='dash')
        ))
        
    # SMA 50
    if 'SMA_50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['SMA_50'],
            name='SMA 50',
            line=dict(color='#2ca02c', width=1.5, dash='dot')
        ))
        
    # EMA 20
    if 'EMA_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['EMA_20'],
            name='EMA 20',
            line=dict(color='#d62728', width=1.5, dash='dashdot')
        ))
        
    fig.update_layout(
        title=f"Historical Price Analysis for {ticker}",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    return fig

def plot_volume(df: pd.DataFrame, ticker: str) -> go.Figure:
    """
    Creates a bar chart showing trading volume.
    """
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df.index, y=df['Volume'],
        name='Volume',
        marker_color='#17becf'
    ))
    
    fig.update_layout(
        title=f"Trading Volume for {ticker}",
        xaxis_title="Date",
        yaxis_title="Volume",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

def plot_forecast(historical_df: pd.DataFrame, forecast_prices: list, ticker: str) -> go.Figure:
    """
    Plots historical close prices followed by forecasted prices, separated by a vertical line.
    """
    fig = go.Figure()
    
    # We display the last 90 days of historical data for context
    hist_subset = historical_df.tail(90)
    
    # Historical Close
    fig.add_trace(go.Scatter(
        x=hist_subset.index, y=hist_subset['Close'],
        name='Historical Close',
        line=dict(color='#1f77b4', width=2.5)
    ))
    
    # Create dates for forecast
    last_date = hist_subset.index[-1]
    forecast_dates = pd.date_range(start=last_date, periods=len(forecast_prices) + 1, freq='B')[1:]
    
    # Connect last historical price with first forecast price to make the line continuous
    connect_x = [last_date] + list(forecast_dates)
    connect_y = [hist_subset['Close'].iloc[-1]] + list(forecast_prices)
    
    # Forecast prices
    fig.add_trace(go.Scatter(
        x=connect_x, y=connect_y,
        name='Forecasted Price',
        line=dict(color='#e377c2', width=2.5, dash='dash')
    ))
    
    # Add vertical line at split point
    fig.add_vline(
        x=last_date,
        line_width=1.5,
        line_dash="dash",
        line_color="yellow",
        annotation_text="Forecast Start",
        annotation_position="top left"
    )
    
    fig.update_layout(
        title=f"Historical & Forecasted Price Trend for {ticker}",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    return fig
