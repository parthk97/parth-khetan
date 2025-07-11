
# intraday_trading_dashboard.py
import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objs as go
from datetime import datetime

st.set_page_config(layout="wide")
st.title("🔍 Intraday Trading Dashboard with Polygon Options Flow")

# --- CONFIG ---
POLYGON_API_KEY = "IDmLEeWgFxIdB8byU95SuPX_1lE0iWUr"
SYMBOL = "SPY"

# --- RSI Calculation ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- Fetch intraday data (Twelve Data) ---
@st.cache_data(ttl=300)
def fetch_intraday_data(symbol):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=300&apikey={POLYGON_API_KEY}"
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

# --- Fetch Polygon options snapshot ---
@st.cache_data(ttl=120)
def fetch_polygon_options_snapshot(symbol):
    url = f"https://api.polygon.io/v3/snapshot/options/{symbol}?apiKey={POLYGON_API_KEY}"
    r = requests.get(url)
    data = r.json()
    return data.get("results", [])

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

# --- Main Logic ---
with st.spinner("Fetching data..."):
    df = fetch_intraday_data(SYMBOL)
    options_data = fetch_polygon_options_snapshot(SYMBOL)

if df.empty:
    st.error("Twelve Data intraday data unavailable.")
else:
    last_time = df.index[-1]
    prior_close = df["close"].iloc[0]
    high = df["high"].max()
    low = df["low"].min()
    pivot = (high + low + prior_close) / 3
    trend = detect_trend(df)
    breakout, recent_high = detect_breakout(df)

    # Sidebar
    st.sidebar.title("📊 Market Snapshot")
    st.sidebar.metric("Last Updated", last_time.strftime("%Y-%m-%d %H:%M"))
    st.sidebar.metric("Prior Close", "%.2f" % prior_close)
    st.sidebar.metric("Day High", "%.2f" % high)
    st.sidebar.metric("Day Low", "%.2f" % low)
    st.sidebar.metric("Pivot", "%.2f" % pivot)
    st.sidebar.metric("Trend", trend)
    if breakout:
        st.sidebar.success("🚨 Breakout > %.2f" % recent_high)
    else:
        st.sidebar.info("Watching > %.2f" % recent_high)

    # Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df["close"], name="Close", line=dict(color="white")))
    fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", yaxis="y2", line=dict(color="green")))
    fig.update_layout(
        template="plotly_dark",
        title="SPY Intraday Chart",
        xaxis=dict(title="Time"),
        yaxis=dict(title="Price"),
        yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100]),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    # Options Flow
    st.subheader("🔥 Options Flow (Live from Polygon.io)")
    if not options_data:
        st.warning("No options data available.")
    else:
        snapshot_df = pd.DataFrame([
            {
                "Symbol": opt["details"]["symbol"],
                "Type": "Call" if "C" in opt["details"]["symbol"] else "Put",
                "Strike": opt["details"]["strike_price"],
                "Expiry": opt["details"]["expiration_date"],
                "OI": opt.get("open_interest", 0),
                "Volume": opt.get("volume", 0)
            }
            for opt in options_data if "details" in opt
        ])
        agg = snapshot_df.groupby(["Strike", "Type"]).agg({"Volume": "sum"}).unstack().fillna(0)
        st.dataframe(agg["Volume"], use_container_width=True)

    st.caption("Data: Twelve Data + Polygon.io")
