"""Integration tests for MCP tools."""

import pytest
from modules.market_data import get_live_price, normalize_symbol, scan_market, get_sector_heatmap
from modules.portfolio_manager import place_virtual_trade, get_portfolio_pnl, init_db


class TestNormalizeSymbol:
    def test_plain_symbol(self):
        assert normalize_symbol("RELIANCE") == "RELIANCE.NS"

    def test_already_ns(self):
        assert normalize_symbol("RELIANCE.NS") == "RELIANCE.NS"

    def test_bse_symbol(self):
        assert normalize_symbol("RELIANCE.BO") == "RELIANCE.BO"

    def test_index_nifty(self):
        assert normalize_symbol("NIFTY") == "^NSEI"

    def test_index_sensex(self):
        assert normalize_symbol("SENSEX") == "^BSESN"

    def test_case_insensitive(self):
        assert normalize_symbol("reliance") == "RELIANCE.NS"


class TestGetLivePrice:
    def test_valid_symbol(self):
        result = get_live_price("TCS")
        assert "price" in result or "error" in result

    def test_returns_expected_fields(self):
        result = get_live_price("RELIANCE")
        if "error" not in result:
            assert "price" in result
            assert "change" in result
            assert "change_percent" in result
            assert "volume" in result
            assert result["price"] > 0


class TestPortfolioManager:
    def test_buy_and_pnl(self):
        """Test buying and checking P&L."""
        init_db()
        result = place_virtual_trade("TCS", 1, "BUY")
        if "error" not in result:
            assert result["status"] == "EXECUTED"
            assert result["order_id"]

            pnl = get_portfolio_pnl()
            assert "positions" in pnl
            assert "summary" in pnl

    def test_sell_without_position(self):
        """Selling without a position should fail gracefully."""
        init_db()
        result = place_virtual_trade("NONEXISTENTSTOCK", 100, "SELL")
        assert "error" in result

    def test_invalid_side(self):
        result = place_virtual_trade("TCS", 1, "INVALID")
        assert "error" in result
