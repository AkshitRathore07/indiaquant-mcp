"""Tests for signal generator logic."""

import pytest
from modules.signal_generator import compute_technicals, generate_signal


class TestComputeTechnicals:
    def test_returns_rsi(self):
        """Technicals should include RSI."""
        result = compute_technicals("RELIANCE", "3mo")
        if "error" not in result:
            assert "rsi" in result
            if result["rsi"] is not None:
                assert 0 <= result["rsi"] <= 100

    def test_returns_macd(self):
        """Technicals should include MACD."""
        result = compute_technicals("TCS", "3mo")
        if "error" not in result:
            assert "macd" in result

    def test_returns_bollinger_bands(self):
        """Technicals should include Bollinger Bands."""
        result = compute_technicals("INFY", "3mo")
        if "error" not in result:
            assert "bollinger_bands" in result

    def test_returns_patterns(self):
        """Technicals should include pattern detection."""
        result = compute_technicals("HDFCBANK", "3mo")
        if "error" not in result:
            assert "patterns" in result
            assert isinstance(result["patterns"], list)


class TestGenerateSignal:
    def test_signal_output_format(self):
        """Signal should have signal, confidence, and breakdown."""
        result = generate_signal("RELIANCE", "3mo")
        if "error" not in result:
            assert result["signal"] in ("BUY", "SELL", "HOLD")
            assert 0 <= result["confidence"] <= 100
            assert "breakdown" in result
            assert "composite_score" in result

    def test_signal_has_technicals(self):
        """Signal should include underlying technical data."""
        result = generate_signal("TCS", "3mo")
        if "error" not in result:
            assert "technicals" in result
