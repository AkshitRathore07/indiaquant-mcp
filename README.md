# IndiaQuant MCP

**Real-time Indian stock market AI assistant** built on Model Context Protocol (MCP). Plugs into Claude Desktop (or any MCP-compatible AI agent) to provide full stock market intelligence + virtual trading capabilities using 100% free APIs.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│               Claude Desktop (Client)            │
│  "Should I buy HDFC Bank right now?"             │
└──────────────────┬──────────────────────────────┘
                   │ MCP Protocol (stdio / SSE)
                   ▼
┌─────────────────────────────────────────────────┐
│            server.py — MCP Tools Layer           │
│  10 registered tools with JSON schemas           │
│  Routes requests → modules                       │
└──────┬───────┬───────┬───────┬──────────────────┘
       │       │       │       │
       ▼       ▼       ▼       ▼
┌────────┐┌────────┐┌────────┐┌────────┐
│ Market ││ Signal ││Options ││Portfol-│
│ Data   ││ Gener- ││ Chain  ││io Risk │
│ Engine ││ ator   ││Analyzer││Manager │
└───┬────┘└───┬────┘└───┬────┘└───┬────┘
    │         │         │         │
    ▼         ▼         ▼         ▼
 yfinance  NewsAPI   yfinance   SQLite
 Alpha V.  VADER     Black-
           pandas-ta Scholes
```

### 5 Modules

| Module | File | Purpose |
|--------|------|---------|
| **Market Data Engine** | `modules/market_data.py` | Live prices, historical OHLCV, sector heatmap, market scanner via yfinance |
| **Signal Generator** | `modules/signal_generator.py` | RSI/MACD/Bollinger via pandas-ta, VADER sentiment on NewsAPI headlines, weighted BUY/SELL/HOLD signal |
| **Options Chain Analyzer** | `modules/options_analyzer.py` | Options chain via yfinance, max pain calculation, OI spike detection, unusual activity alerts |
| **Black-Scholes Greeks** | `modules/black_scholes.py` | Pure mathematical Black-Scholes: Delta, Gamma, Theta, Vega, IV — no pricing libraries |
| **Portfolio Risk Manager** | `modules/portfolio_manager.py` | Virtual portfolio in SQLite, live P&L, stop-loss/target tracking, volatility-based risk scoring |

### 10 MCP Tools

| # | Tool | Input | Output |
|---|------|-------|--------|
| 1 | `tool_get_live_price` | symbol | price, change%, volume |
| 2 | `tool_get_options_chain` | symbol, expiry | strikes, CE/PE OI, max pain, PCR |
| 3 | `tool_analyze_sentiment` | symbol | score, headlines, signal |
| 4 | `tool_generate_signal` | symbol, timeframe | BUY/SELL/HOLD, confidence |
| 5 | `tool_get_portfolio_pnl` | — | positions, total P&L |
| 6 | `tool_place_virtual_trade` | symbol, qty, side | order_id, status |
| 7 | `tool_calculate_greeks` | symbol, strike, expiry, type | delta, gamma, theta, vega |
| 8 | `tool_detect_unusual_activity` | symbol | alerts, anomalies |
| 9 | `tool_scan_market` | filter criteria | matching symbols |
| 10 | `tool_get_sector_heatmap` | — | sectors with % change |

---

## Free API Stack

| Purpose | API | Limits |
|---------|-----|--------|
| Live NSE/BSE prices | yfinance | Unlimited, free |
| Historical OHLC | yfinance | Full history, free |
| Options chain | yfinance | Free, NSE supported |
| News & sentiment | NewsAPI.org | 100 req/day free |
| Macro indicators | Alpha Vantage | 25 req/day free |
| Technical analysis | pandas-ta | Fully free, open source |
| Greeks calculation | Custom Black-Scholes | From scratch |

---

## Setup Guide

### Prerequisites

- Python 3.11+
- [Claude Desktop](https://claude.ai/download) installed

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/indiaquant-mcp.git
cd indiaquant-mcp

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### 2. Get API Keys (Free)

1. **NewsAPI**: Register at [newsapi.org](https://newsapi.org/register) → get free key
2. **Alpha Vantage**: Get key at [alphavantage.co](https://www.alphavantage.co/support/#api-key)

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Connect to Claude Desktop

Edit Claude Desktop config file:

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add this to the config:

```json
{
  "mcpServers": {
    "indiaquant": {
      "command": "python",
      "args": ["C:\\FULL\\PATH\\TO\\indiaquant-mcp\\server.py"],
      "env": {
        "NEWSAPI_KEY": "your_key_here",
        "ALPHA_VANTAGE_KEY": "your_key_here"
      }
    }
  }
}
```

> **Important**: Use the full absolute path to `server.py`. On Windows, use double backslashes.

### 5. Restart Claude Desktop

Close and reopen Claude Desktop. You should see a 🔧 (hammer) icon in the chat input box — click it to verify all 10 IndiaQuant tools are listed.

### 6. Test It

Ask Claude:
- *"What's the live price of Reliance?"*
- *"Generate a signal for HDFC Bank"*
- *"Buy 10 shares of TCS"*
- *"Show my portfolio P&L"*
- *"What's the max pain for Nifty?"*

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run only Black-Scholes tests (offline, no API needed)
pytest tests/test_black_scholes.py -v

# Run signal/tool tests (needs internet)
pytest tests/test_signals.py tests/test_tools.py -v
```

---

## Deploy on Render (24/7 Availability)

See the **Deployment Guide** section below for full step-by-step instructions.

### Quick Steps

1. Push code to GitHub
2. Create a new **Web Service** on [render.com](https://render.com)
3. Connect your GitHub repo
4. Set build command: `pip install -e .`
5. Set start command: `python server.py --transport sse`
6. Add environment variables (API keys)
7. Deploy

Then update Claude Desktop config to use the SSE endpoint:

```json
{
  "mcpServers": {
    "indiaquant": {
      "url": "https://your-app.onrender.com/sse"
    }
  }
}
```

---

## Design Decisions & Trade-offs

### Caching Strategy
- **30s TTL** for live prices — balances freshness vs. rate limits
- **5min TTL** for options chain — chains don't change drastically
- **1hr TTL** for news sentiment — avoid burning NewsAPI free quota
- **In-memory** (cachetools) — simple, no Redis needed for single-server

### Signal Confidence Scoring
- **40% technicals** (RSI, MACD, Bollinger) — most reliable for short-term
- **30% sentiment** (VADER on news headlines) — captures market mood
- **30% trend/patterns** (SMA crossovers, chart patterns) — confirms direction
- Score maps to 0–100 confidence via distance from neutral (50)

### Black-Scholes Implementation
- Pure math with `scipy.stats.norm` for CDF/PDF only (standard normal distribution)
- Newton-Raphson for implied volatility calculation
- Per-day theta (divided by 365) for practical use
- Vega per 1% volatility change for readability

### Portfolio Manager
- SQLite for zero-config persistence — portfolio survives restarts
- Position averaging on repeated buys of same stock
- Risk score based on annualized historical volatility (3-month window)

### Edge Case Handling
- Market holidays: yfinance returns last available data, cache prevents redundant calls
- Missing data: graceful fallbacks (signal works on technicals alone if news API fails)
- Symbol normalization: auto-appends `.NS`, handles indices like NIFTY → `^NSEI`

---

## Project Structure

```
indiaquant-mcp/
├── server.py                  # MCP server entry point (10 tools)
├── config.py                  # API keys, constants, sector maps
├── pyproject.toml             # Dependencies
├── .env.example               # Environment template
├── .gitignore
├── README.md
├── modules/
│   ├── __init__.py
│   ├── market_data.py         # Module 1: yfinance + caching
│   ├── signal_generator.py    # Module 2: TA + sentiment
│   ├── options_analyzer.py    # Module 3: chain + Greeks
│   ├── black_scholes.py       # Pure Black-Scholes implementation
│   ├── portfolio_manager.py   # Module 4: SQLite + risk
│   └── cache.py               # TTL cache wrapper
└── tests/
    ├── __init__.py
    ├── test_black_scholes.py   # Greeks math validation
    ├── test_signals.py         # Signal generator tests
    └── test_tools.py           # Integration tests
```

---

## License

MIT
