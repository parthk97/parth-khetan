
# intraday_trading_dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objs as go
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("🔍 Intraday Trading Dashboard with Signals")

# --- CONFIG ---
API_KEY = "b7050ef20f2c49efa202154cb3c7a620"
SYMBOL = "SPY"
INTERVAL = "5min"
LIMIT = 300

# --- Fetch intraday data ---
@st.cache_data(ttl=300)
def fetch_intraday_data(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={INTERVAL}&outputsize={LIMIT}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return pd.DataFrame()
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)
    df = df.sort_index()
    df = df.astype(float)
    df["VWAP"] = (df["high"] + df["low"] + df["close"]) / 3
    df["RSI"] = calculate_rsi(df["close"])
    return df

# --- RSI Function ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- Signal Detection ---
def detect_trend(df):
    window = 10
    df["slope"] = df["close"].rolling(window).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
    latest_slope = df["slope"].iloc[-1]
    if latest_slope > 0.2:
        return "📈 Strong Uptrend"
    elif latest_slope < -0.2:
        return "📉 Strong Downtrend"
    else:
        return "🔁 Sideways / Choppy"

def detect_breakout(df):
    recent_high = df["high"].iloc[-20:-1].max()
    latest_price = df["close"].iloc[-1]
    breakout = latest_price > recent_high
    return breakout, recent_high

# --- Fetch mock options flow ---
def get_mock_options_flow():
    return pd.DataFrame({
        "Strike": [430, 435, 440, 445],
        "Calls": [1200, 1800, 950, 700],
        "Puts": [800, 900, 1600, 1900]
    })

# --- Main Dashboard Logic ---
with st.spinner("Fetching market data..."):
    df = fetch_intraday_data(SYMBOL)

if df.empty:
    st.error("Failed to load data from Twelve Data API.")
else:
    last_time = df.index[-1]
    prior_close = df["close"].iloc[0]
    high = df["high"].max()
    low = df["low"].min()
    pivot = (high + low + prior_close) / 3

    # Trend & breakout
    trend = detect_trend(df)
    breakout, recent_high = detect_breakout(df)

    # --- Sidebar ---
    st.sidebar.title("📊 Market Snapshot")
    st.sidebar.metric("Last Updated", last_time.strftime("%Y-%m-%d %H:%M"))
    st.sidebar.metric("Prior Close", "{:.2f}".format(prior_close))
    st.sidebar.metric("Day High", "{:.2f}".format(high))
    st.sidebar.metric("Day Low", "{:.2f}".format(low))
    st.sidebar.metric("Pivot Point", "{:.2f}".format(pivot))
    st.sidebar.metric("Current Trend", trend)
    if breakout:
        st.sidebar.success("🚨 Breakout above {:.2f}!".format(recent_high))
    else:
        st.sidebar.info("Watching for breakout > {:.2f}".format(recent_high))

    # --- Chart ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Close", line=dict(color="white")))
    fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", yaxis="y2", line=dict(color="green")))
    fig.update_layout(
        template="plotly_dark",
        title=f"{SYMBOL} Intraday Chart",
        xaxis=dict(title="Time"),
        yaxis=dict(title="Price"),
        yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100]),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- Options Flow Heatmap ---
    st.subheader("🔥 Mock Options Flow Heatmap")
    opt_df = get_mock_options_flow()
    st.dataframe(opt_df.set_index("Strike"), use_container_width=True)

    st.caption("Real-time data via Twelve Data. Options flow is mock data for now.")
