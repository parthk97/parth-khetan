
# intraday_trading_dashboard.py
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt
import requests
import plotly.graph_objs as go

st.set_page_config(layout="wide")
st.title("🔍 Intraday Trading Dashboard")

# ---- Functions ----
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_vwap(data):
    vwap = (data['Volume'] * (data['High'] + data['Low'] + data['Close']) / 3).cumsum() / data['Volume'].cumsum()
    return vwap

def fetch_data(symbol, interval='5m', period='1d'):
    df = yf.download(tickers=symbol, interval=interval, period=period)
    df.dropna(inplace=True)
    if df.empty:
        return df
    df['RSI'] = calculate_rsi(df)
    df['VWAP'] = calculate_vwap(df)
    return df

def fetch_vix():
    vix = yf.download("^VIX", interval="1m", period="1d")
    if vix.empty:
        return None
    return vix['Close'].iloc[-1]

def fetch_put_call_ratio():
    return 0.91  # Placeholder

def get_spx_levels(df):
    if df.empty:
        return None, None, None, None
    prior_close = df['Close'].iloc[0]
    high = df['High'].max()
    low = df['Low'].min()
    pivot = (high + low + prior_close) / 3
    return prior_close, high, low, pivot

# ---- Fetch Data ----
with st.spinner("Loading data..."):
    spx_df = fetch_data("^GSPC")
    if spx_df.empty:
        st.warning("⚠️ SPX data unavailable — falling back to SPY ETF.")
        spx_df = fetch_data("SPY")

    if spx_df.empty:
        st.error("⚠️ Neither SPX nor SPY data is available. Please check back later.")
    else:
        vix = fetch_vix()
        vix_display = f"{vix:.2f}" if vix else "N/A"
        pcr = fetch_put_call_ratio()
        prior_close, high, low, pivot = get_spx_levels(spx_df)

        # ---- Pre-market Bias ----
        bias = "📈 Bullish Bias" if spx_df['Close'].iloc[-1] > prior_close else "📉 Bearish Bias"

        # ---- Sidebar ----
        st.sidebar.title("🔢 Market Snapshot")
        st.sidebar.metric("VIX", vix_display)
        st.sidebar.metric("Put/Call Ratio", f"{pcr:.2f}")
        st.sidebar.metric("Pre-market Bias", bias)
        st.sidebar.markdown("---")
        st.sidebar.metric("Prior Close", f"{prior_close:.2f}")
        st.sidebar.metric("Day High", f"{high:.2f}")
        st.sidebar.metric("Day Low", f"{low:.2f}")
        st.sidebar.metric("Pivot Point", f"{pivot:.2f}")

        # ---- Chart ----
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=spx_df.index, y=spx_df['Close'], name="Price", line=dict(color="white")))
        fig.add_trace(go.Scatter(x=spx_df.index, y=spx_df['VWAP'], name="VWAP", line=dict(color="orange")))
        fig.add_trace(go.Scatter(x=spx_df.index, y=spx_df['RSI'], name="RSI", yaxis='y2', line=dict(color="green")))

        fig.update_layout(
            template="plotly_dark",
            title="Intraday Chart with VWAP & RSI",
            xaxis=dict(title="Time"),
            yaxis=dict(title="Price"),
            yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0,100]),
            height=600
        )

        st.plotly_chart(fig, use_container_width=True)

        # ---- Sentiment Panel ----
        sentiment = "🚀 Risk-On" if vix and vix < 18 and pcr < 1.0 else "⚠️ Risk-Off"
        st.success(f"Current Sentiment: {sentiment}")

        st.caption("Data via Yahoo Finance. For informational use only.")
