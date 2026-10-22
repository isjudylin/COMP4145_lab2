from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from trading_strategy import run_backtest


st.set_page_config(page_title="Trading Strategy Dashboard", layout="wide")


@st.cache_data
def load_results(symbol: str = "AAPL", start: str = "2022-01-01"):
    return run_backtest(symbol=symbol, start=start)


symbol = st.sidebar.selectbox("Ticker", ["AAPL", "MSFT", "NVDA", "GOOG", "AMZN"])
start_date = st.sidebar.date_input("Start date", value=pd.Timestamp("2022-01-01").date())

results = load_results(symbol=symbol, start=start_date.isoformat())
price_data = results["data"]
trades = results["trades"].copy()
buy_signals = results["buy_signals"].copy()
sell_signals = results["sell_signals"].copy()
stats = results["statistics"]

if not price_data.empty:
    price_data["date"] = pd.to_datetime(price_data["date"])

if not buy_signals.empty:
    buy_signals["date"] = pd.to_datetime(buy_signals["date"])

if not sell_signals.empty:
    sell_signals["date"] = pd.to_datetime(sell_signals["date"])

if not trades.empty:
    trades["entry_date"] = pd.to_datetime(trades["entry_date"])
    trades["exit_date"] = pd.to_datetime(trades["exit_date"])

st.title(f"{symbol} Golden Cross Backtest Dashboard")

selected_tab = st.radio(
    "Navigation",
    ["Price Chart", "Trade Statistics", "Detailed Trades"],
    horizontal=True,
)

if selected_tab == "Price Chart":
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=price_data["date"],
            y=price_data["close"],
            mode="lines",
            name="Price",
            line={"color": "#1f77b4", "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=price_data["date"],
            y=price_data["short_ma"],
            mode="lines",
            name="Short MA",
            line={"color": "#ff7f0e", "width": 2},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=price_data["date"],
            y=price_data["long_ma"],
            mode="lines",
            name="Long MA",
            line={"color": "#2ca02c", "width": 2},
        )
    )

    if not buy_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=buy_signals["date"],
                y=buy_signals["price"],
                mode="markers",
                name="Buy",
                marker={"color": "green", "size": 10, "symbol": "circle"},
            )
        )

    if not sell_signals.empty:
        fig.add_trace(
            go.Scatter(
                x=sell_signals["date"],
                y=sell_signals["price"],
                mode="markers",
                name="Sell",
                marker={"color": "red", "size": 10, "symbol": "circle"},
            )
        )

    fig.update_layout(
        title=f"{symbol} Price, Short MA and Long MA",
        xaxis_title="Date",
        yaxis_title="Price",
        template="plotly_white",
        height=700,
    )
    st.plotly_chart(fig, use_container_width=True)

elif selected_tab == "Trade Statistics":
    st.subheader("Overall Trade Statistics")

    kpis = [
        ("Total trades", stats["total_trades"]),
        ("Total profit", f"${stats['total_profit']:.2f}"),
        ("Win rate", f"{stats['win_rate'] * 100:.1f}%"),
        ("Average return", f"{stats['average_return'] * 100:.2f}%"),
        ("Gross return", f"{stats['gross_return'] * 100:.2f}%"),
        ("Average holding days", f"{stats['avg_holding_days']:.1f}"),
    ]

    cols = st.columns(len(kpis))
    for col, (label, value) in zip(cols, kpis):
        col.metric(label, value)

    if not trades.empty:
        summary_df = pd.DataFrame(
            {
                "Metric": [
                    "Total trades",
                    "Total profit",
                    "Win rate",
                    "Average return",
                    "Gross return",
                    "Best trade",
                    "Worst trade",
                    "Average holding days",
                ],
                "Value": [
                    stats["total_trades"],
                    f"${stats['total_profit']:.2f}",
                    f"{stats['win_rate'] * 100:.1f}%",
                    f"{stats['average_return'] * 100:.2f}%",
                    f"{stats['gross_return'] * 100:.2f}%",
                    f"${stats['best_trade']:.2f}",
                    f"${stats['worst_trade']:.2f}",
                    f"{stats['avg_holding_days']:.1f} days",
                ],
            }
        )
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades were generated for this date range.")

else:
    st.subheader("Detailed Trade Record")
    if trades.empty:
        st.info("There are no completed trades to display.")
    else:
        display_df = trades[["entry_date", "exit_date", "entry_price", "exit_price", "pnl", "return_pct", "holding_days"]].copy()
        display_df["entry_price"] = display_df["entry_price"].map(lambda value: f"${value:.2f}")
        display_df["exit_price"] = display_df["exit_price"].map(lambda value: f"${value:.2f}")
        display_df["pnl"] = display_df["pnl"].map(lambda value: f"${value:.2f}")
        display_df["return_pct"] = display_df["return_pct"].map(lambda value: f"{value * 100:.2f}%")
        display_df["entry_date"] = display_df["entry_date"].dt.strftime("%Y-%m-%d")
        display_df["exit_date"] = display_df["exit_date"].dt.strftime("%Y-%m-%d")
        st.dataframe(display_df, use_container_width=True, hide_index=True)

st.caption("Strategy: 20-day MA crosses above 50-day MA = buy; 20-day MA crosses below 50-day MA = sell.")
