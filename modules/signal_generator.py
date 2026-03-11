"""AI Trade Signal Generator - Technicals + Sentiment → BUY/SELL/HOLD."""

import ta as ta_lib
import httpx
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from modules.market_data import get_historical_data, get_live_price, normalize_symbol
from modules.cache import get_cached, set_cached
from config import NEWSAPI_KEY


_sentiment_analyzer = SentimentIntensityAnalyzer()


def compute_technicals(symbol: str, timeframe: str = "1mo") -> dict:
    """Compute RSI, MACD, Bollinger Bands for a symbol."""
    hist = get_historical_data(symbol, period=timeframe)
    if hist.empty or len(hist) < 20:
        return {"error": f"Insufficient data for {symbol} (need 20+ bars, got {len(hist)})"}

    close = hist["Close"]

    # RSI (14-period)
    rsi_series = ta_lib.momentum.RSIIndicator(close, window=14).rsi()
    current_rsi = float(rsi_series.iloc[-1]) if rsi_series is not None and not rsi_series.empty else None

    # MACD (12, 26, 9)
    macd_ind = ta_lib.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd_val = None
    macd_signal = None
    macd_hist = None
    try:
        macd_val = float(macd_ind.macd().iloc[-1])
        macd_signal = float(macd_ind.macd_signal().iloc[-1])
        macd_hist = float(macd_ind.macd_diff().iloc[-1])
    except Exception:
        pass

    # Bollinger Bands (20, 2)
    bb_ind = ta_lib.volatility.BollingerBands(close, window=20, window_dev=2)
    bb_upper = bb_middle = bb_lower = None
    try:
        bb_upper = float(bb_ind.bollinger_hband().iloc[-1])
        bb_middle = float(bb_ind.bollinger_mavg().iloc[-1])
        bb_lower = float(bb_ind.bollinger_lband().iloc[-1])
    except Exception:
        pass

    current_price = float(close.iloc[-1])

    # Pattern detection
    patterns = detect_patterns(hist)

    return {
        "current_price": round(current_price, 2),
        "rsi": round(current_rsi, 2) if current_rsi else None,
        "macd": {
            "value": round(macd_val, 4) if macd_val else None,
            "signal": round(macd_signal, 4) if macd_signal else None,
            "histogram": round(macd_hist, 4) if macd_hist else None,
        },
        "bollinger_bands": {
            "upper": round(bb_upper, 2) if bb_upper else None,
            "middle": round(bb_middle, 2) if bb_middle else None,
            "lower": round(bb_lower, 2) if bb_lower else None,
        },
        "patterns": patterns,
    }


def detect_patterns(hist) -> list:
    """Simple chart pattern detection on OHLC data."""
    patterns_found = []
    close = hist["Close"].values
    high = hist["High"].values
    low = hist["Low"].values
    n = len(close)

    if n < 20:
        return patterns_found

    # Double Top Detection (simplified)
    # Look for two peaks with a valley in between in last 20 bars
    window = close[-20:]
    peak_indices = []
    for i in range(1, len(window) - 1):
        if window[i] > window[i - 1] and window[i] > window[i + 1]:
            peak_indices.append(i)

    if len(peak_indices) >= 2:
        last_two = peak_indices[-2:]
        p1, p2 = window[last_two[0]], window[last_two[1]]
        if abs(p1 - p2) / p1 < 0.02:  # Peaks within 2%
            patterns_found.append("Double Top (bearish)")

    # Double Bottom Detection
    trough_indices = []
    for i in range(1, len(window) - 1):
        if window[i] < window[i - 1] and window[i] < window[i + 1]:
            trough_indices.append(i)

    if len(trough_indices) >= 2:
        last_two = trough_indices[-2:]
        t1, t2 = window[last_two[0]], window[last_two[1]]
        if abs(t1 - t2) / t1 < 0.02:
            patterns_found.append("Double Bottom (bullish)")

    # Trend detection
    sma5 = sum(close[-5:]) / 5
    sma20 = sum(close[-20:]) / 20
    if sma5 > sma20 * 1.01:
        patterns_found.append("Short-term Uptrend (SMA5 > SMA20)")
    elif sma5 < sma20 * 0.99:
        patterns_found.append("Short-term Downtrend (SMA5 < SMA20)")

    return patterns_found


def analyze_sentiment(symbol: str) -> dict:
    """Analyze news sentiment for a symbol using NewsAPI + VADER."""
    sym = normalize_symbol(symbol)
    clean_name = sym.replace(".NS", "").replace(".BO", "")

    cache_key = f"sentiment_{clean_name}"
    cached = get_cached("news", cache_key)
    if cached:
        return cached

    headlines = []
    sentiment_scores = []

    if NEWSAPI_KEY:
        try:
            resp = httpx.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": f"{clean_name} stock India",
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 10,
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=10,
            )
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                for article in articles:
                    title = article.get("title", "")
                    if title and title != "[Removed]":
                        score = _sentiment_analyzer.polarity_scores(title)
                        headlines.append({
                            "title": title,
                            "sentiment": score["compound"],
                        })
                        sentiment_scores.append(score["compound"])
        except Exception:
            pass

    if not sentiment_scores:
        result = {
            "symbol": clean_name,
            "sentiment_score": 0,
            "signal": "NEUTRAL",
            "headlines": [],
            "note": "No news data available (check NEWSAPI_KEY)",
        }
    else:
        avg_score = sum(sentiment_scores) / len(sentiment_scores)
        if avg_score > 0.15:
            signal = "BULLISH"
        elif avg_score < -0.15:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        result = {
            "symbol": clean_name,
            "sentiment_score": round(avg_score, 4),
            "signal": signal,
            "headlines_analyzed": len(headlines),
            "headlines": headlines[:5],  # Top 5
        }

    set_cached("news", cache_key, result)
    return result


def generate_signal(symbol: str, timeframe: str = "3mo") -> dict:
    """Generate composite BUY/SELL/HOLD signal with confidence score.

    Weighting:
    - 40% Technical indicators (RSI, MACD, Bollinger)
    - 30% Sentiment analysis
    - 30% Trend / pattern alignment
    """
    technicals = compute_technicals(symbol, timeframe)
    if "error" in technicals:
        return technicals

    sentiment = analyze_sentiment(symbol)
    price_data = get_live_price(symbol)

    # --- Technical Score (0 to 100, 50 = neutral) ---
    tech_score = 50  # neutral baseline

    rsi = technicals.get("rsi")
    if rsi is not None:
        if rsi < 30:
            tech_score += 20  # Oversold → bullish
        elif rsi < 40:
            tech_score += 10
        elif rsi > 70:
            tech_score -= 20  # Overbought → bearish
        elif rsi > 60:
            tech_score -= 10

    macd = technicals.get("macd", {})
    macd_hist = macd.get("histogram")
    if macd_hist is not None:
        if macd_hist > 0:
            tech_score += 15  # Bullish momentum
        else:
            tech_score -= 15

    bb = technicals.get("bollinger_bands", {})
    current_price = technicals["current_price"]
    bb_lower = bb.get("lower")
    bb_upper = bb.get("upper")
    if bb_lower and bb_upper:
        if current_price <= bb_lower:
            tech_score += 15  # Near lower band → oversold
        elif current_price >= bb_upper:
            tech_score -= 15  # Near upper band → overbought

    tech_score = max(0, min(100, tech_score))

    # --- Sentiment Score (0 to 100) ---
    sent_raw = sentiment.get("sentiment_score", 0)
    # Map [-1, 1] → [0, 100]
    sent_score = (sent_raw + 1) * 50

    # --- Trend Score (0 to 100) ---
    trend_score = 50
    patterns = technicals.get("patterns", [])
    for p in patterns:
        if "bullish" in p.lower() or "uptrend" in p.lower():
            trend_score += 15
        elif "bearish" in p.lower() or "downtrend" in p.lower():
            trend_score -= 15
    trend_score = max(0, min(100, trend_score))

    # --- Weighted Composite ---
    composite = (tech_score * 0.4) + (sent_score * 0.3) + (trend_score * 0.3)

    if composite >= 65:
        signal = "BUY"
    elif composite <= 35:
        signal = "SELL"
    else:
        signal = "HOLD"

    # Confidence: distance from 50 (neutral)
    confidence = min(100, abs(composite - 50) * 2)

    return {
        "symbol": symbol,
        "signal": signal,
        "confidence": round(confidence, 1),
        "composite_score": round(composite, 2),
        "breakdown": {
            "technical_score": round(tech_score, 2),
            "sentiment_score": round(sent_score, 2),
            "trend_score": round(trend_score, 2),
            "weights": "40% tech + 30% sentiment + 30% trend",
        },
        "technicals": technicals,
        "sentiment_summary": sentiment.get("signal", "NEUTRAL"),
        "price": price_data if "error" not in price_data else None,
    }
