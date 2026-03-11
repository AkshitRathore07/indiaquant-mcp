"""Market Data Engine - Fetch live & historical NSE/BSE data via yfinance."""

import yfinance as yf
import pandas as pd
from modules.cache import get_cached, set_cached
from config import INDICES, SECTOR_MAP


def normalize_symbol(symbol: str) -> str:
    """Normalize symbol to yfinance format (append .NS if needed)."""
    symbol = symbol.strip().upper()

    # Check if it's a known index
    if symbol in INDICES:
        return INDICES[symbol]

    # Already has exchange suffix
    if symbol.endswith((".NS", ".BO")):
        return symbol

    # Check for index prefix
    if symbol.startswith("^"):
        return symbol

    # Default to NSE
    return f"{symbol}.NS"


def get_live_price(symbol: str) -> dict:
    """Fetch live price data for a symbol."""
    sym = normalize_symbol(symbol)
    cached = get_cached("price", sym)
    if cached:
        return cached

    ticker = yf.Ticker(sym)
    info = ticker.fast_info

    try:
        hist = ticker.history(period="2d")
        if hist.empty:
            return {"error": f"No data found for {sym}. Check symbol."}

        current_price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current_price
        change = current_price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        volume = int(hist["Volume"].iloc[-1])

        result = {
            "symbol": sym,
            "price": round(current_price, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_percent": round(change_pct, 2),
            "volume": volume,
            "currency": "INR",
        }
        set_cached("price", sym, result)
        return result
    except Exception as e:
        return {"error": f"Failed to fetch price for {sym}: {str(e)}"}


def get_historical_data(symbol: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV historical data."""
    sym = normalize_symbol(symbol)
    cache_key = f"{sym}_{period}_{interval}"
    cached = get_cached("history", cache_key)
    if cached is not None:
        return cached

    ticker = yf.Ticker(sym)
    hist = ticker.history(period=period, interval=interval)

    if not hist.empty:
        set_cached("history", cache_key, hist)
    return hist


def get_sector_heatmap() -> dict:
    """Get performance of all sectors based on constituent stocks."""
    heatmap = {}

    for sector, symbols in SECTOR_MAP.items():
        changes = []
        for sym in symbols:
            try:
                data = get_live_price(sym.replace(".NS", ""))
                if "error" not in data:
                    changes.append(data["change_percent"])
            except Exception:
                continue

        if changes:
            avg_change = sum(changes) / len(changes)
            heatmap[sector] = {
                "average_change_percent": round(avg_change, 2),
                "stocks_tracked": len(changes),
                "top_gainer": None,
                "top_loser": None,
            }
        else:
            heatmap[sector] = {
                "average_change_percent": 0,
                "stocks_tracked": 0,
                "top_gainer": None,
                "top_loser": None,
            }

    return heatmap


def scan_market(filter_criteria: dict) -> list:
    """Scan market based on filter criteria.

    Supported filters:
    - sector: str (e.g., "IT", "Banking")
    - min_change: float (minimum % change)
    - max_change: float (maximum % change)
    - min_volume: int
    - rsi_below: float (requires historical data)
    - rsi_above: float
    """
    import pandas_ta as ta

    sector = filter_criteria.get("sector")
    min_change = filter_criteria.get("min_change")
    max_change = filter_criteria.get("max_change")
    min_volume = filter_criteria.get("min_volume")
    rsi_below = filter_criteria.get("rsi_below")
    rsi_above = filter_criteria.get("rsi_above")

    # Determine symbol universe
    if sector and sector in SECTOR_MAP:
        symbols = SECTOR_MAP[sector]
    else:
        symbols = [s for syms in SECTOR_MAP.values() for s in syms]

    results = []
    for sym in symbols:
        try:
            data = get_live_price(sym.replace(".NS", ""))
            if "error" in data:
                continue

            # Apply price change filters
            if min_change is not None and data["change_percent"] < min_change:
                continue
            if max_change is not None and data["change_percent"] > max_change:
                continue
            if min_volume is not None and data["volume"] < min_volume:
                continue

            # RSI filter requires historical data
            if rsi_below is not None or rsi_above is not None:
                hist = get_historical_data(sym.replace(".NS", ""), period="1mo")
                if not hist.empty and len(hist) >= 14:
                    rsi = ta.rsi(hist["Close"], length=14)
                    current_rsi = float(rsi.iloc[-1]) if not rsi.empty else None
                    if current_rsi is not None:
                        if rsi_below is not None and current_rsi >= rsi_below:
                            continue
                        if rsi_above is not None and current_rsi <= rsi_above:
                            continue
                        data["rsi"] = round(current_rsi, 2)
                    else:
                        continue
                else:
                    continue

            results.append(data)
        except Exception:
            continue

    return results
