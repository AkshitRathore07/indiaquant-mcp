"""IndiaQuant MCP Server - 10 tools for Indian stock market intelligence."""

from mcp.server.fastmcp import FastMCP
from modules.market_data import get_live_price, scan_market, get_sector_heatmap
from modules.signal_generator import generate_signal, analyze_sentiment
from modules.options_analyzer import (
    get_options_chain,
    detect_unusual_activity,
    calculate_greeks_for_contract,
)
from modules.portfolio_manager import place_virtual_trade, get_portfolio_pnl

# Create MCP server
mcp = FastMCP(
    "IndiaQuant MCP",
    description="Real-time Indian stock market AI assistant with 10 intelligence tools",
)


# ──────────────────────────────────────────────
# Tool 1: get_live_price
# ──────────────────────────────────────────────
@mcp.tool()
def tool_get_live_price(symbol: str) -> dict:
    """Get the live/latest price for an Indian stock or index.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "TCS", "NIFTY", "HDFCBANK").
                Automatically appends .NS for NSE. Use .BO suffix for BSE.

    Returns:
        Current price, change, change%, volume, and previous close.
    """
    return get_live_price(symbol)


# ──────────────────────────────────────────────
# Tool 2: get_options_chain
# ──────────────────────────────────────────────
@mcp.tool()
def tool_get_options_chain(symbol: str, expiry: str = "") -> dict:
    """Get the full options chain (calls + puts) for a symbol with max pain.

    Args:
        symbol: Stock or index symbol (e.g., "RELIANCE", "NIFTY").
        expiry: Optional expiry date (YYYY-MM-DD). Uses nearest expiry if blank.

    Returns:
        Calls/puts with strike, OI, volume, IV. Plus max pain & PCR.
    """
    return get_options_chain(symbol, expiry if expiry else None)


# ──────────────────────────────────────────────
# Tool 3: analyze_sentiment
# ──────────────────────────────────────────────
@mcp.tool()
def tool_analyze_sentiment(symbol: str) -> dict:
    """Analyze news sentiment for a stock using NewsAPI headlines + VADER.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "INFY").

    Returns:
        Sentiment score (-1 to 1), BULLISH/BEARISH/NEUTRAL signal, and top headlines.
    """
    return analyze_sentiment(symbol)


# ──────────────────────────────────────────────
# Tool 4: generate_signal
# ──────────────────────────────────────────────
@mcp.tool()
def tool_generate_signal(symbol: str, timeframe: str = "3mo") -> dict:
    """Generate a composite BUY/SELL/HOLD signal with confidence score.

    Combines technical analysis (RSI, MACD, Bollinger Bands, patterns) with
    news sentiment to produce a weighted signal.

    Args:
        symbol: Stock symbol (e.g., "HDFCBANK", "TCS").
        timeframe: Historical period for technicals ("1mo", "3mo", "6mo", "1y").

    Returns:
        Signal (BUY/SELL/HOLD), confidence (0-100%), score breakdown, and technicals.
    """
    return generate_signal(symbol, timeframe)


# ──────────────────────────────────────────────
# Tool 5: get_portfolio_pnl
# ──────────────────────────────────────────────
@mcp.tool()
def tool_get_portfolio_pnl() -> dict:
    """Get your virtual portfolio with real-time P&L for all positions.

    Returns:
        All positions with current prices, P&L, risk scores, stop-loss/target status.
        Plus portfolio summary: total invested, current value, cash balance.
    """
    return get_portfolio_pnl()


# ──────────────────────────────────────────────
# Tool 6: place_virtual_trade
# ──────────────────────────────────────────────
@mcp.tool()
def tool_place_virtual_trade(
    symbol: str, quantity: int, side: str, stop_loss: float = 0, target: float = 0
) -> dict:
    """Place a virtual BUY or SELL trade at current market price.

    Starts with ₹10,00,000 virtual cash. Supports stop-loss and target.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "TCS").
        quantity: Number of shares to trade.
        side: "BUY" or "SELL".
        stop_loss: Optional stop-loss price (0 = none).
        target: Optional target price (0 = none).

    Returns:
        Order ID, execution price, trade value, remaining cash.
    """
    return place_virtual_trade(
        symbol,
        quantity,
        side,
        stop_loss if stop_loss > 0 else None,
        target if target > 0 else None,
    )


# ──────────────────────────────────────────────
# Tool 7: calculate_greeks
# ──────────────────────────────────────────────
@mcp.tool()
def tool_calculate_greeks(
    symbol: str, strike: float, expiry: str, option_type: str = "CE", risk_free_rate: float = 0.07
) -> dict:
    """Calculate option Greeks (Delta, Gamma, Theta, Vega) using Black-Scholes.

    Implemented from scratch — no external pricing libraries.

    Args:
        symbol: Underlying stock symbol (e.g., "RELIANCE").
        strike: Strike price of the option.
        expiry: Expiry date (YYYY-MM-DD).
        option_type: "CE" for Call, "PE" for Put.
        risk_free_rate: Risk-free rate (default 0.07 = 7%).

    Returns:
        Delta, Gamma, Theta (daily), Vega (per 1% vol), theoretical price.
    """
    return calculate_greeks_for_contract(symbol, strike, expiry, option_type, risk_free_rate)


# ──────────────────────────────────────────────
# Tool 8: detect_unusual_activity
# ──────────────────────────────────────────────
@mcp.tool()
def tool_detect_unusual_activity(symbol: str) -> dict:
    """Detect unusual options activity for a symbol via volume/OI spikes.

    Flags contracts where volume > 3x open interest as unusual.

    Args:
        symbol: Stock symbol (e.g., "RELIANCE", "NIFTY").

    Returns:
        Alert list with strike, volume, OI, severity. Top OI positions. PCR & max pain.
    """
    return detect_unusual_activity(symbol)


# ──────────────────────────────────────────────
# Tool 9: scan_market
# ──────────────────────────────────────────────
@mcp.tool()
def tool_scan_market(
    sector: str = "",
    min_change: float = -100,
    max_change: float = 100,
    min_volume: int = 0,
    rsi_below: float = 0,
    rsi_above: float = 0,
) -> dict:
    """Scan the market with filters to find matching stocks.

    Args:
        sector: Filter by sector ("IT", "Banking", "Auto", "Pharma", "Energy",
                "FMCG", "Metals", "Finance", "Infra"). Empty = all sectors.
        min_change: Minimum % change filter (-100 = no filter).
        max_change: Maximum % change filter (100 = no filter).
        min_volume: Minimum volume filter (0 = no filter).
        rsi_below: Only stocks with RSI below this value (0 = no filter).
        rsi_above: Only stocks with RSI above this value (0 = no filter).

    Returns:
        List of matching stocks with price data and optional RSI.
    """
    criteria = {}
    if sector:
        criteria["sector"] = sector
    if min_change > -100:
        criteria["min_change"] = min_change
    if max_change < 100:
        criteria["max_change"] = max_change
    if min_volume > 0:
        criteria["min_volume"] = min_volume
    if rsi_below > 0:
        criteria["rsi_below"] = rsi_below
    if rsi_above > 0:
        criteria["rsi_above"] = rsi_above

    results = scan_market(criteria)
    return {"matches": results, "count": len(results), "filters_applied": criteria}


# ──────────────────────────────────────────────
# Tool 10: get_sector_heatmap
# ──────────────────────────────────────────────
@mcp.tool()
def tool_get_sector_heatmap() -> dict:
    """Get a sector-wise performance heatmap of the Indian market.

    Covers: IT, Banking, Auto, Pharma, Energy, FMCG, Metals, Finance, Infra.

    Returns:
        Each sector's average % change, stocks tracked count.
    """
    return get_sector_heatmap()


# ──────────────────────────────────────────────
# Run the server
# ──────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
