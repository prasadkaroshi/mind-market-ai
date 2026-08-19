from __future__ import annotations

import math
from typing import Any

import pandas as pd
import yfinance as yf

try:
    import pandas_ta as ta  # type: ignore
except ModuleNotFoundError:
    import pandas_ta_classic as ta  # type: ignore


def _number(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_stock_data(ticker: str, timeframe: str) -> tuple[dict[str, Any], pd.DataFrame]:
    symbol = ticker.strip().upper()
    periods = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y"}
    period = {"1M": "6mo", "3M": "6mo", "6M": "1y", "1Y": "2y", "2Y": "2y"}.get(timeframe, "6mo")
    market = yf.Ticker(f"{symbol}.NS")
    info = market.info or {}
    history = market.history(period=period, interval="1d")
    if not history.empty:
        history = history[history["Volume"] > 0]
    if not history.empty and all(column in history for column in ("High", "Low", "Close")):
        history.ta.sma(length=20, append=True)
        history.ta.sma(length=50, append=True)
        history.ta.sma(length=20, volume=history["Volume"], append=True, col_names=("VOL_SMA_20",))
        history.ta.atr(length=14, append=True)
    return info, history


def technical_analysis(history: pd.DataFrame, timeframe: str) -> dict[str, Any]:
    required = ("ATRr_14", "SMA_20", "SMA_50", "VOL_SMA_20")
    if history.empty or len(history) < 50:
        raise ValueError("Not enough price history for technical analysis.")
    if not all(column in history for column in required):
        raise ValueError("Technical indicators could not be calculated.")

    previous = history.iloc[-2]
    latest = history.iloc[-1]
    pivot = (previous["High"] + previous["Low"] + previous["Close"]) / 3
    resistance = (2 * pivot) - previous["Low"]
    support = (2 * pivot) - previous["High"]
    price = float(latest["Close"])
    atr = _number(latest["ATRr_14"]) or 0
    trend = "Up" if price > pivot else "Down"
    confirmations = [
        {"label": "Price vs pivot", "passed": bool(price > pivot)},
        {"label": "20-day MA vs 50-day MA", "passed": bool(latest["SMA_20"] > latest["SMA_50"])},
        {"label": "Volume vs 20-day average", "passed": bool(latest["Volume"] > latest["VOL_SMA_20"])},
    ]
    target = resistance if trend == "Up" else support
    stop_loss = support if trend == "Up" else resistance
    projection = None
    if atr and ((trend == "Up" and resistance > price) or (trend == "Down" and support < price)):
        projection = math.ceil(abs(target - price) / atr)

    chart_points = {"1M": 23, "3M": 66, "6M": 132, "1Y": 252, "2Y": 504}.get(timeframe, 66)
    chart = []
    for index, row in history.tail(chart_points).iterrows():
        chart.append({
            "date": index.strftime("%Y-%m-%d"),
            "open": _number(row["Open"]),
            "high": _number(row["High"]),
            "low": _number(row["Low"]),
            "close": _number(row["Close"]),
            "sma20": _number(row["SMA_20"]),
            "sma50": _number(row["SMA_50"]),
        })
    return {
        "trend": trend,
        "price": price,
        "target": _number(target),
        "stopLoss": _number(stop_loss),
        "support": _number(support),
        "resistance": _number(resistance),
        "confirmationScore": int(sum(bool(item["passed"]) for item in confirmations)),
        "confirmations": confirmations,
        "projectionDays": projection,
        "chart": chart,
    }


def fundamental_snapshot(info: dict[str, Any]) -> dict[str, Any]:
    values = {
        "pe": _number(info.get("trailingPE")),
        "pb": _number(info.get("priceToBook")),
        "roe": _number(info.get("returnOnEquity")),
        "currentRatio": _number(info.get("currentRatio")),
    }
    available = [value for value in values.values() if value is not None]
    score = round(sum(available) / len(available), 2) if available else None
    return {"score": score, "recommendation": "Review data" if score is None else "Market snapshot", "metrics": values}


def analyze_stock(ticker: str, timeframe: str = "3M") -> dict[str, Any]:
    symbol = ticker.strip().upper()
    if not symbol:
        raise ValueError("Enter an NSE ticker symbol.")
    selected_timeframe = timeframe.upper()
    info, history = get_stock_data(symbol, selected_timeframe)
    if history.empty:
        raise ValueError(f"No market data found for {symbol}.")
    technical = technical_analysis(history, selected_timeframe)
    return {
        "ticker": symbol,
        "timeframe": selected_timeframe,
        "companyName": info.get("longName") or info.get("shortName") or symbol,
        "currency": info.get("currency") or "INR",
        "marketCap": _number(info.get("marketCap")),
        "technical": technical,
        "fundamental": fundamental_snapshot(info),
    }
