from typing import Dict, Tuple
from math import isfinite


def distance_weighted_base(
    prices: Dict[str, float], distances: Dict[str, float]
) -> float:
    weights = {}
    for m, p in prices.items():
        d = max(0.0, float(distances.get(m, 0.0)))
        weights[m] = 1.0 / (1.0 + d)
    z = sum(weights.values()) or 1.0
    return sum(weights[m] * prices[m] for m in prices) / z


def ewma(curr: float, prev: float | None, alpha: float = 0.4) -> float:
    if prev is None:
        return curr
    return alpha * curr + (1 - alpha) * prev


def estimate(
    prices_now: Dict[str, float],
    distances: Dict[str, float],
    prev_base: float | None,
    season_index: float = 0.0,
    logistics_mode: str = "wholesale",
    shock_index: float = 0.0,
    variety_grade_factor: float = 1.0,
    weather_index: float = 0.0,
    k1: float = 0.12,
    k2: float = 0.08,
    k3: float = 0.12,
    alpha: float = 0.4,
) -> Tuple[float, Tuple[float, float], Dict]:
    base_raw = distance_weighted_base(prices_now, distances)
    base_smoothed = ewma(base_raw, prev_base, alpha)

    logistics_map = {"farmgate": 0.90, "wholesale": 1.00, "retail": 1.20}
    adj_season = 1 + k1 * season_index
    adj_logistics = logistics_map.get(logistics_mode, 1.0)
    adj_shock = 1 + k2 * shock_index
    adj_weather = 1 + k3 * weather_index

    p_hat = (
        base_smoothed
        * adj_season
        * adj_logistics
        * adj_shock
        * adj_weather
        * variety_grade_factor
    )

    # fallback sigma based on scale (caller should compute real residual sigma)
    sigma = max(0.5, 0.03 * p_hat) if isfinite(p_hat) else 1.0

    explain = {
        "base_smoothed": round(base_smoothed, 3),
        "season_mult": round(adj_season, 3),
        "logistics_mult": round(adj_logistics, 3),
        "shock_mult": round(adj_shock, 3),
        "weather_mult": round(adj_weather, 3),
        "variety_mult": round(variety_grade_factor, 3),
    }
    return float(p_hat), (float(p_hat - sigma), float(p_hat + sigma)), explain
