from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


def fetch_market_data(symbol: str = "AAPL", start: str = "2022-01-01", end: str | None = None) -> pd.DataFrame:
    """Download market price data for a given stock symbol."""
    data = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
    if data.empty:
        raise ValueError(f"No data returned for symbol '{symbol}'")

    data = data.reset_index()

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            str(col[0]).lower() if isinstance(col, tuple) else str(col).lower()
            for col in data.columns
        ]
    else:
        data.columns = [str(col).lower() for col in data.columns]

    if "date" not in data.columns and "datetime" in data.columns:
        data = data.rename(columns={"datetime": "date"})

    if "date" in data.columns:
        data["date"] = pd.to_datetime(data["date"])

    if "adj close" in data.columns and "close" not in data.columns:
        data["close"] = data["adj close"]

    required = ["date", "open", "high", "low", "close", "volume"]
    missing = [col for col in required if col not in data.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}. Actual columns: {list(data.columns)}")

    return data[required].dropna().reset_index(drop=True)


def add_moving_averages(data: pd.DataFrame, short_window: int = 20, long_window: int = 50) -> pd.DataFrame:
    """Add short- and long-term moving averages to market data."""
    result = data.copy()
    result["short_ma"] = result["close"].rolling(window=short_window, min_periods=1).mean()
    result["long_ma"] = result["close"].rolling(window=long_window, min_periods=1).mean()
    return result


def run_backtest(
    symbol: str = "AAPL",
    start: str = "2022-01-01",
    end: str | None = None,
    short_window: int = 20,
    long_window: int = 50,
) -> dict[str, Any]:
    """Run a simple golden-cross strategy and return data and trade metrics."""
    market_data = add_moving_averages(fetch_market_data(symbol=symbol, start=start, end=end), short_window, long_window)

    buy_signals: list[dict[str, Any]] = []
    sell_signals: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []

    position = 0
    entry_date: pd.Timestamp | None = None
    entry_price: float | None = None

    for index, row in market_data.iterrows():
        previous_row = market_data.iloc[index - 1] if index > 0 else None

        if position == 0:
            if previous_row is not None and previous_row["short_ma"] <= previous_row["long_ma"] and row["short_ma"] > row["long_ma"]:
                entry_date = row["date"]
                entry_price = float(row["close"])
                buy_signals.append({"date": entry_date, "price": entry_price})
                position = 1
        elif position == 1:
            if previous_row is not None and previous_row["short_ma"] >= previous_row["long_ma"] and row["short_ma"] < row["long_ma"]:
                exit_date = row["date"]
                exit_price = float(row["close"])
                pnl = (exit_price - entry_price) if entry_price is not None else 0.0
                pct_return = ((exit_price - entry_price) / entry_price) if entry_price else 0.0
                holding_days = (exit_date - entry_date).days if entry_date is not None else 0

                trades.append(
                    {
                        "entry_date": entry_date,
                        "exit_date": exit_date,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "pnl": pnl,
                        "return_pct": pct_return,
                        "holding_days": holding_days,
                    }
                )
                sell_signals.append({"date": exit_date, "price": exit_price})
                position = 0
                entry_date = None
                entry_price = None

    trade_df = pd.DataFrame(trades)

    if trade_df.empty:
        stats = {
            "total_trades": 0,
            "total_profit": 0.0,
            "win_rate": 0.0,
            "average_return": 0.0,
            "gross_return": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "avg_holding_days": 0.0,
        }
    else:
        stats = {
            "total_trades": int(len(trade_df)),
            "total_profit": float(trade_df["pnl"].sum()),
            "win_rate": float((trade_df["pnl"] > 0).mean()),
            "average_return": float(trade_df["return_pct"].mean()),
            "gross_return": float(trade_df["return_pct"].sum()),
            "best_trade": float(trade_df["pnl"].max()),
            "worst_trade": float(trade_df["pnl"].min()),
            "avg_holding_days": float(trade_df["holding_days"].mean()),
        }

    return {
        "symbol": symbol,
        "data": market_data,
        "buy_signals": pd.DataFrame(buy_signals),
        "sell_signals": pd.DataFrame(sell_signals),
        "trades": trade_df,
        "statistics": stats,
    }


if __name__ == "__main__":
    results = run_backtest(symbol="AAPL", start="2022-01-01")
    print(results["statistics"])
    print(results["trades"].head())
