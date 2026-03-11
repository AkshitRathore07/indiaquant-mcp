"""Portfolio Risk Manager - Virtual portfolio with SQLite persistence."""

import sqlite3
import os
import uuid
from datetime import datetime
from modules.market_data import get_live_price, get_historical_data
from config import DEFAULT_CASH_BALANCE

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "portfolio.db")


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the SQLite database with required tables."""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
            stop_loss REAL,
            target REAL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            side TEXT NOT NULL CHECK(side IN ('BUY', 'SELL')),
            status TEXT NOT NULL DEFAULT 'EXECUTED',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            cash_balance REAL NOT NULL
        )
    """)

    # Initialize account if not exists
    cursor.execute("SELECT cash_balance FROM account WHERE id = 1")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO account (id, cash_balance) VALUES (1, ?)", (DEFAULT_CASH_BALANCE,))

    conn.commit()
    conn.close()


def place_virtual_trade(symbol: str, quantity: int, side: str, stop_loss: float = None, target: float = None) -> dict:
    """Place a virtual trade (BUY or SELL).

    Args:
        symbol: Stock symbol
        quantity: Number of shares
        side: "BUY" or "SELL"
        stop_loss: Optional stop-loss price
        target: Optional target price
    """
    side = side.upper()
    if side not in ("BUY", "SELL"):
        return {"error": "Side must be BUY or SELL"}
    if quantity <= 0:
        return {"error": "Quantity must be positive"}

    price_data = get_live_price(symbol)
    if "error" in price_data:
        return price_data

    current_price = price_data["price"]
    trade_value = current_price * quantity

    conn = _get_conn()
    cursor = conn.cursor()

    try:
        # Check cash for BUY
        cursor.execute("SELECT cash_balance FROM account WHERE id = 1")
        cash = cursor.fetchone()["cash_balance"]

        if side == "BUY":
            if trade_value > cash:
                conn.close()
                return {"error": f"Insufficient cash. Need ₹{trade_value:.2f}, have ₹{cash:.2f}"}

            # Deduct cash
            cursor.execute("UPDATE account SET cash_balance = cash_balance - ? WHERE id = 1", (trade_value,))

            # Check if position exists
            cursor.execute("SELECT * FROM portfolio WHERE symbol = ? AND side = 'BUY'", (symbol,))
            existing = cursor.fetchone()

            if existing:
                # Average up/down
                new_qty = existing["quantity"] + quantity
                new_avg = ((existing["avg_price"] * existing["quantity"]) + (current_price * quantity)) / new_qty
                cursor.execute(
                    "UPDATE portfolio SET quantity = ?, avg_price = ?, stop_loss = COALESCE(?, stop_loss), target = COALESCE(?, target) WHERE id = ?",
                    (new_qty, new_avg, stop_loss, target, existing["id"])
                )
            else:
                pos_id = str(uuid.uuid4())[:8]
                cursor.execute(
                    "INSERT INTO portfolio (id, symbol, quantity, avg_price, side, stop_loss, target, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (pos_id, symbol, quantity, current_price, side, stop_loss, target, datetime.now().isoformat())
                )

        elif side == "SELL":
            cursor.execute("SELECT * FROM portfolio WHERE symbol = ? AND side = 'BUY'", (symbol,))
            existing = cursor.fetchone()

            if not existing or existing["quantity"] < quantity:
                conn.close()
                available = existing["quantity"] if existing else 0
                return {"error": f"Insufficient shares. Have {available}, trying to sell {quantity}"}

            # Add cash
            cursor.execute("UPDATE account SET cash_balance = cash_balance + ? WHERE id = 1", (trade_value,))

            new_qty = existing["quantity"] - quantity
            if new_qty == 0:
                cursor.execute("DELETE FROM portfolio WHERE id = ?", (existing["id"],))
            else:
                cursor.execute("UPDATE portfolio SET quantity = ? WHERE id = ?", (new_qty, existing["id"]))

        # Record trade
        trade_id = str(uuid.uuid4())[:8]
        cursor.execute(
            "INSERT INTO trades (id, symbol, quantity, price, side, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (trade_id, symbol, quantity, current_price, side, datetime.now().isoformat())
        )

        conn.commit()

        cursor.execute("SELECT cash_balance FROM account WHERE id = 1")
        new_cash = cursor.fetchone()["cash_balance"]

        result = {
            "order_id": trade_id,
            "status": "EXECUTED",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": current_price,
            "trade_value": round(trade_value, 2),
            "remaining_cash": round(new_cash, 2),
        }

        if stop_loss:
            result["stop_loss"] = stop_loss
        if target:
            result["target"] = target

        return result

    except Exception as e:
        conn.rollback()
        return {"error": f"Trade failed: {str(e)}"}
    finally:
        conn.close()


def get_portfolio_pnl() -> dict:
    """Get current portfolio with real-time P&L calculation."""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM portfolio")
    positions = cursor.fetchall()

    cursor.execute("SELECT cash_balance FROM account WHERE id = 1")
    cash = cursor.fetchone()["cash_balance"]

    conn.close()

    portfolio_positions = []
    total_invested = 0
    total_current = 0

    for pos in positions:
        price_data = get_live_price(pos["symbol"])
        current_price = price_data.get("price", pos["avg_price"])

        invested = pos["avg_price"] * pos["quantity"]
        current_val = current_price * pos["quantity"]
        pnl = current_val - invested
        pnl_pct = (pnl / invested) * 100 if invested else 0

        # Risk score based on historical volatility
        risk_score = _calculate_risk_score(pos["symbol"])

        # Check stop-loss and target
        sl_hit = pos["stop_loss"] and current_price <= pos["stop_loss"]
        target_hit = pos["target"] and current_price >= pos["target"]

        position_data = {
            "symbol": pos["symbol"],
            "quantity": pos["quantity"],
            "avg_price": round(pos["avg_price"], 2),
            "current_price": round(current_price, 2),
            "invested_value": round(invested, 2),
            "current_value": round(current_val, 2),
            "pnl": round(pnl, 2),
            "pnl_percent": round(pnl_pct, 2),
            "risk_score": risk_score,
            "stop_loss": pos["stop_loss"],
            "target": pos["target"],
            "stop_loss_hit": sl_hit,
            "target_hit": target_hit,
        }
        portfolio_positions.append(position_data)

        total_invested += invested
        total_current += current_val

    total_pnl = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested) * 100 if total_invested else 0
    portfolio_value = cash + total_current

    return {
        "positions": portfolio_positions,
        "summary": {
            "total_positions": len(portfolio_positions),
            "total_invested": round(total_invested, 2),
            "total_current_value": round(total_current, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round(total_pnl_pct, 2),
            "cash_balance": round(cash, 2),
            "portfolio_value": round(portfolio_value, 2),
        },
    }


def _calculate_risk_score(symbol: str) -> dict:
    """Calculate risk score based on historical volatility (annualized)."""
    try:
        hist = get_historical_data(symbol, period="3mo")
        if hist.empty or len(hist) < 10:
            return {"score": "N/A", "volatility": "N/A"}

        import numpy as np
        returns = np.log(hist["Close"] / hist["Close"].shift(1)).dropna()
        daily_vol = float(returns.std())
        annual_vol = daily_vol * np.sqrt(252)

        if annual_vol > 0.40:
            risk_label = "HIGH"
        elif annual_vol > 0.25:
            risk_label = "MEDIUM"
        else:
            risk_label = "LOW"

        return {
            "score": risk_label,
            "annual_volatility": round(annual_vol * 100, 2),
            "daily_volatility": round(daily_vol * 100, 2),
        }
    except Exception:
        return {"score": "N/A", "volatility": "N/A"}


# Initialize DB on import
init_db()
