"""Tests for Black-Scholes Greeks implementation."""

import math
import pytest
from modules.black_scholes import (
    black_scholes_price,
    calculate_delta,
    calculate_gamma,
    calculate_theta,
    calculate_vega,
    calculate_all_greeks,
    implied_volatility,
)


class TestBlackScholesPrice:
    """Test the Black-Scholes pricing formula."""

    def test_call_price_atm(self):
        """ATM call should have a positive price."""
        price = black_scholes_price(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="CE")
        assert price > 0
        # ATM 1-year call with 20% vol should be around 10.45
        assert 8 < price < 13

    def test_put_price_atm(self):
        """ATM put should have a positive price."""
        price = black_scholes_price(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="PE")
        assert price > 0

    def test_put_call_parity(self):
        """Put-call parity: C - P = S - K*exp(-rT)."""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.20
        call = black_scholes_price(S, K, T, r, sigma, "CE")
        put = black_scholes_price(S, K, T, r, sigma, "PE")
        parity = S - K * math.exp(-r * T)
        assert abs((call - put) - parity) < 0.01

    def test_deep_itm_call(self):
        """Deep ITM call should be close to intrinsic value."""
        price = black_scholes_price(S=150, K=100, T=0.01, r=0.05, sigma=0.20, option_type="CE")
        assert price > 49  # Intrinsic = 50

    def test_deep_otm_call(self):
        """Deep OTM call should be close to zero."""
        price = black_scholes_price(S=50, K=100, T=0.01, r=0.05, sigma=0.20, option_type="CE")
        assert price < 1

    def test_at_expiry_call(self):
        """At expiry, call = max(S-K, 0)."""
        assert black_scholes_price(S=110, K=100, T=0, r=0.05, sigma=0.20, option_type="CE") == 10
        assert black_scholes_price(S=90, K=100, T=0, r=0.05, sigma=0.20, option_type="CE") == 0

    def test_at_expiry_put(self):
        """At expiry, put = max(K-S, 0)."""
        assert black_scholes_price(S=90, K=100, T=0, r=0.05, sigma=0.20, option_type="PE") == 10
        assert black_scholes_price(S=110, K=100, T=0, r=0.05, sigma=0.20, option_type="PE") == 0


class TestDelta:
    def test_call_delta_range(self):
        """Call delta should be between 0 and 1."""
        d = calculate_delta(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="CE")
        assert 0 < d < 1

    def test_put_delta_range(self):
        """Put delta should be between -1 and 0."""
        d = calculate_delta(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="PE")
        assert -1 < d < 0

    def test_atm_call_delta_near_half(self):
        """ATM call delta should be near 0.5."""
        d = calculate_delta(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="CE")
        assert 0.45 < d < 0.65

    def test_deep_itm_call_delta(self):
        """Deep ITM call delta should be near 1."""
        d = calculate_delta(S=200, K=100, T=0.5, r=0.05, sigma=0.20, option_type="CE")
        assert d > 0.95


class TestGamma:
    def test_gamma_positive(self):
        """Gamma should always be positive."""
        g = calculate_gamma(S=100, K=100, T=1.0, r=0.05, sigma=0.20)
        assert g > 0

    def test_gamma_highest_atm(self):
        """Gamma is highest at ATM."""
        g_atm = calculate_gamma(S=100, K=100, T=0.1, r=0.05, sigma=0.20)
        g_otm = calculate_gamma(S=100, K=120, T=0.1, r=0.05, sigma=0.20)
        assert g_atm > g_otm


class TestTheta:
    def test_call_theta_negative(self):
        """Call theta should be negative (time decay)."""
        t = calculate_theta(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="CE")
        assert t < 0

    def test_put_theta_usually_negative(self):
        """ATM put theta is typically negative."""
        t = calculate_theta(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="PE")
        assert t < 0


class TestVega:
    def test_vega_positive(self):
        """Vega should be positive."""
        v = calculate_vega(S=100, K=100, T=1.0, r=0.05, sigma=0.20)
        assert v > 0

    def test_vega_highest_atm(self):
        """Vega is highest for ATM options."""
        v_atm = calculate_vega(S=100, K=100, T=1.0, r=0.05, sigma=0.20)
        v_otm = calculate_vega(S=100, K=150, T=1.0, r=0.05, sigma=0.20)
        assert v_atm > v_otm


class TestAllGreeks:
    def test_returns_all_fields(self):
        """calculate_all_greeks should return all expected fields."""
        result = calculate_all_greeks(S=100, K=100, T=1.0, r=0.05, sigma=0.20, option_type="CE")
        assert "price" in result
        assert "delta" in result
        assert "gamma" in result
        assert "theta" in result
        assert "vega" in result
        assert result["option_type"] == "CE"


class TestImpliedVolatility:
    def test_iv_recovery(self):
        """IV calculation should recover the original volatility."""
        S, K, T, r, sigma = 100, 100, 1.0, 0.05, 0.25
        price = black_scholes_price(S, K, T, r, sigma, "CE")
        iv = implied_volatility(price, S, K, T, r, "CE")
        assert abs(iv - sigma) < 0.01  # Within 1% tolerance

    def test_iv_put(self):
        """IV should also work for puts."""
        S, K, T, r, sigma = 100, 105, 0.5, 0.05, 0.30
        price = black_scholes_price(S, K, T, r, sigma, "PE")
        iv = implied_volatility(price, S, K, T, r, "PE")
        assert abs(iv - sigma) < 0.01
