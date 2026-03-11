"""Options Chain Analyzer - OI analysis, max pain, unusual activity detection."""

import yfinance as yf
from datetime import datetime
from modules.market_data import normalize_symbol, get_live_price
from modules.black_scholes import calculate_all_greeks, implied_volatility
from modules.cache import get_cached, set_cached


def get_options_chain(symbol: str, expiry: str = None) -> dict:
    """Fetch options chain data for a symbol.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "NIFTY")
        expiry: Expiry date string (YYYY-MM-DD). If None, uses nearest expiry.
    """
    sym = normalize_symbol(symbol)
    cache_key = f"options_{sym}_{expiry}"
    cached = get_cached("options", cache_key)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(sym)
        expiries = ticker.options  # Tuple of expiry date strings

        if not expiries:
            return {"error": f"No options data available for {sym}"}

        # Select expiry
        if expiry and expiry in expiries:
            selected_expiry = expiry
        else:
            selected_expiry = expiries[0]  # nearest

        chain = ticker.option_chain(selected_expiry)
        calls = chain.calls
        puts = chain.puts

        # Get current price for reference
        price_data = get_live_price(symbol)
        current_price = price_data.get("price", 0)

        # Format calls
        call_data = []
        for _, row in calls.iterrows():
            call_data.append({
                "strike": float(row["strike"]),
                "lastPrice": float(row.get("lastPrice", 0)),
                "bid": float(row.get("bid", 0)),
                "ask": float(row.get("ask", 0)),
                "volume": int(row.get("volume", 0)) if not _is_nan(row.get("volume")) else 0,
                "openInterest": int(row.get("openInterest", 0)) if not _is_nan(row.get("openInterest")) else 0,
                "impliedVolatility": round(float(row.get("impliedVolatility", 0)), 4),
            })

        # Format puts
        put_data = []
        for _, row in puts.iterrows():
            put_data.append({
                "strike": float(row["strike"]),
                "lastPrice": float(row.get("lastPrice", 0)),
                "bid": float(row.get("bid", 0)),
                "ask": float(row.get("ask", 0)),
                "volume": int(row.get("volume", 0)) if not _is_nan(row.get("volume")) else 0,
                "openInterest": int(row.get("openInterest", 0)) if not _is_nan(row.get("openInterest")) else 0,
                "impliedVolatility": round(float(row.get("impliedVolatility", 0)), 4),
            })

        # Calculate max pain
        max_pain = _calculate_max_pain(call_data, put_data)

        result = {
            "symbol": sym,
            "expiry": selected_expiry,
            "available_expiries": list(expiries),
            "underlying_price": current_price,
            "calls": call_data,
            "puts": put_data,
            "max_pain": max_pain,
            "total_call_oi": sum(c["openInterest"] for c in call_data),
            "total_put_oi": sum(p["openInterest"] for p in put_data),
            "pcr": round(
                sum(p["openInterest"] for p in put_data) /
                max(sum(c["openInterest"] for c in call_data), 1),
                4
            ),
        }
        set_cached("options", cache_key, result)
        return result

    except Exception as e:
        return {"error": f"Failed to fetch options chain for {sym}: {str(e)}"}


def _is_nan(value) -> bool:
    """Check if a value is NaN."""
    try:
        import math
        return math.isnan(float(value))
    except (ValueError, TypeError):
        return True


def _calculate_max_pain(calls: list, puts: list) -> dict:
    """Calculate max pain - the strike at which option writers have minimum loss."""
    strikes = sorted(set(c["strike"] for c in calls) | set(p["strike"] for p in puts))

    if not strikes:
        return {"strike": 0, "total_pain": 0}

    call_oi = {c["strike"]: c["openInterest"] for c in calls}
    put_oi = {p["strike"]: p["openInterest"] for p in puts}

    min_pain = float("inf")
    max_pain_strike = 0

    for test_strike in strikes:
        total_pain = 0

        # Pain for call writers: if price > strike, call buyers exercise
        for strike, oi in call_oi.items():
            if test_strike > strike:
                total_pain += (test_strike - strike) * oi

        # Pain for put writers: if price < strike, put buyers exercise
        for strike, oi in put_oi.items():
            if test_strike < strike:
                total_pain += (strike - test_strike) * oi

        if total_pain < min_pain:
            min_pain = total_pain
            max_pain_strike = test_strike

    return {
        "strike": max_pain_strike,
        "total_pain_value": min_pain,
    }


def detect_unusual_activity(symbol: str) -> dict:
    """Detect unusual options activity via volume/OI spike analysis."""
    chain = get_options_chain(symbol)
    if "error" in chain:
        return chain

    alerts = []

    # Analyze calls
    for opt in chain["calls"]:
        vol = opt["volume"]
        oi = opt["openInterest"]
        if oi > 0 and vol > 0:
            vol_oi_ratio = vol / oi
            if vol_oi_ratio > 3:  # Volume > 3x OI is unusual
                alerts.append({
                    "type": "CALL",
                    "strike": opt["strike"],
                    "volume": vol,
                    "open_interest": oi,
                    "vol_oi_ratio": round(vol_oi_ratio, 2),
                    "severity": "HIGH" if vol_oi_ratio > 5 else "MEDIUM",
                    "signal": "Unusual call buying activity",
                })

    # Analyze puts
    for opt in chain["puts"]:
        vol = opt["volume"]
        oi = opt["openInterest"]
        if oi > 0 and vol > 0:
            vol_oi_ratio = vol / oi
            if vol_oi_ratio > 3:
                alerts.append({
                    "type": "PUT",
                    "strike": opt["strike"],
                    "volume": vol,
                    "open_interest": oi,
                    "vol_oi_ratio": round(vol_oi_ratio, 2),
                    "severity": "HIGH" if vol_oi_ratio > 5 else "MEDIUM",
                    "signal": "Unusual put buying activity",
                })

    # Check for OI spikes (top 5 by OI for calls and puts)
    all_opts = (
        [{"type": "CALL", **c} for c in chain["calls"]] +
        [{"type": "PUT", **p} for p in chain["puts"]]
    )
    all_opts.sort(key=lambda x: x["openInterest"], reverse=True)
    top_oi = all_opts[:5]

    return {
        "symbol": chain["symbol"],
        "expiry": chain["expiry"],
        "unusual_activity_alerts": alerts,
        "alert_count": len(alerts),
        "top_oi_positions": [
            {
                "type": o["type"],
                "strike": o["strike"],
                "open_interest": o["openInterest"],
                "volume": o["volume"],
            }
            for o in top_oi
        ],
        "pcr": chain["pcr"],
        "max_pain": chain["max_pain"],
    }


def calculate_greeks_for_contract(
    symbol: str,
    strike: float,
    expiry: str,
    option_type: str = "CE",
    risk_free_rate: float = 0.07,
) -> dict:
    """Calculate Greeks for a specific option contract.

    Args:
        symbol: Underlying stock symbol
        strike: Strike price
        expiry: Expiry date (YYYY-MM-DD)
        option_type: "CE" for call, "PE" for put
        risk_free_rate: Annualized risk-free rate (default 7% for India)
    """
    price_data = get_live_price(symbol)
    if "error" in price_data:
        return price_data

    S = price_data["price"]
    K = strike

    # Calculate time to expiry in years
    try:
        expiry_date = datetime.strptime(expiry, "%Y-%m-%d")
        now = datetime.now()
        days_to_expiry = max((expiry_date - now).days, 0)
        T = days_to_expiry / 365.0
    except ValueError:
        return {"error": f"Invalid expiry date format: {expiry}. Use YYYY-MM-DD."}

    # Try to get IV from the chain, otherwise estimate from historical vol
    chain = get_options_chain(symbol, expiry)
    sigma = 0.20  # default 20%

    if "error" not in chain:
        opts = chain["calls"] if option_type == "CE" else chain["puts"]
        for opt in opts:
            if abs(opt["strike"] - K) < 0.01:
                if opt["impliedVolatility"] > 0:
                    sigma = opt["impliedVolatility"]
                break

    greeks = calculate_all_greeks(S, K, T, risk_free_rate, sigma, option_type)
    greeks["days_to_expiry"] = days_to_expiry
    greeks["expiry"] = expiry
    greeks["symbol"] = symbol

    return greeks
