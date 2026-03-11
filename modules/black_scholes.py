"""Black-Scholes Option Pricing & Greeks - Implemented from scratch.

No external options pricing libraries used.
Only uses scipy.stats.norm for the standard normal CDF/PDF (pure math function).
"""

import math
from scipy.stats import norm


def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "CE") -> float:
    """Calculate Black-Scholes option price.

    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate (annualized, e.g., 0.07 for 7%)
        sigma: Volatility (annualized, e.g., 0.20 for 20%)
        option_type: "CE" for call, "PE" for put
    """
    if T <= 0:
        # At expiry
        if option_type == "CE":
            return max(S - K, 0)
        return max(K - S, 0)

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "CE":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return price


def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "CE") -> float:
    """Calculate Delta - rate of change of option price w.r.t. underlying price."""
    if T <= 0:
        if option_type == "CE":
            return 1.0 if S > K else 0.0
        return -1.0 if S < K else 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))

    if option_type == "CE":
        return norm.cdf(d1)
    return norm.cdf(d1) - 1


def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Gamma - rate of change of Delta w.r.t. underlying price.
    Same for both calls and puts.
    """
    if T <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return norm.pdf(d1) / (S * sigma * math.sqrt(T))


def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "CE") -> float:
    """Calculate Theta - rate of change of option price w.r.t. time (per day).
    Returns daily theta (divided by 365).
    """
    if T <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    common_term = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))

    if option_type == "CE":
        theta = common_term - r * K * math.exp(-r * T) * norm.cdf(d2)
    else:
        theta = common_term + r * K * math.exp(-r * T) * norm.cdf(-d2)

    # Return per-day theta
    return theta / 365


def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate Vega - rate of change of option price w.r.t. volatility.
    Returns vega per 1% change in volatility.
    Same for both calls and puts.
    """
    if T <= 0:
        return 0.0

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    # Vega per 1% vol change
    return S * norm.pdf(d1) * math.sqrt(T) / 100


def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "CE") -> dict:
    """Calculate all Greeks for an option contract.

    Args:
        S: Current underlying price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free interest rate (e.g., 0.07)
        sigma: Implied volatility (e.g., 0.20)
        option_type: "CE" for call, "PE" for put

    Returns:
        Dict with price, delta, gamma, theta, vega
    """
    return {
        "option_type": option_type,
        "underlying_price": round(S, 2),
        "strike": round(K, 2),
        "time_to_expiry_years": round(T, 6),
        "risk_free_rate": r,
        "volatility": round(sigma, 4),
        "price": round(black_scholes_price(S, K, T, r, sigma, option_type), 2),
        "delta": round(calculate_delta(S, K, T, r, sigma, option_type), 4),
        "gamma": round(calculate_gamma(S, K, T, r, sigma), 6),
        "theta": round(calculate_theta(S, K, T, r, sigma, option_type), 4),
        "vega": round(calculate_vega(S, K, T, r, sigma), 4),
    }


def implied_volatility(market_price: float, S: float, K: float, T: float, r: float,
                        option_type: str = "CE", tol: float = 1e-6, max_iter: int = 100) -> float:
    """Calculate implied volatility using Newton-Raphson method."""
    if T <= 0:
        return 0.0

    sigma = 0.25  # Initial guess

    for _ in range(max_iter):
        price = black_scholes_price(S, K, T, r, sigma, option_type)
        diff = price - market_price

        if abs(diff) < tol:
            return sigma

        vega_val = calculate_vega(S, K, T, r, sigma) * 100  # Undo the /100 in vega
        if vega_val < 1e-10:
            break

        sigma -= diff / vega_val
        sigma = max(sigma, 0.01)  # Floor at 1%

    return sigma
