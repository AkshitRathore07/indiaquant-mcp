import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")

# Cache TTLs (seconds)
PRICE_CACHE_TTL = 30
OPTIONS_CACHE_TTL = 300
NEWS_CACHE_TTL = 3600
HISTORY_CACHE_TTL = 600

# Portfolio defaults
DEFAULT_CASH_BALANCE = 1_000_000.0  # 10 Lakh virtual cash

# Nifty 50 sector mapping
SECTOR_MAP = {
    "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIMindtree.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS", "INDUSINDBK.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS", "ADANIGREEN.NS", "COALINDIA.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "TATACONSUM.NS"],
    "Metals": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "ADANIENT.NS"],
    "Finance": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS"],
    "Infra": ["LTIM.NS", "ULTRACEMCO.NS", "GRASIM.NS", "ADANIPORTS.NS"],
}

# Common index symbols
INDICES = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}
