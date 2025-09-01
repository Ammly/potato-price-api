from app.estimator import distance_weighted_base, ewma, estimate

class TestEstimator:
    def test_distance_weighted_base(self):
        prices = {"Nairobi": 100.0, "Nakuru": 90.0, "Nyeri": 95.0}
        distances = {"Nairobi": 0.0, "Nakuru": 50.0, "Nyeri": 30.0}
        
        result = distance_weighted_base(prices, distances)
        
        # Should weight closer markets more heavily
        assert isinstance(result, float)
        assert result > 0
        # Nairobi (distance 0) should have highest weight
        assert 95 < result <= 100

    def test_ewma(self):
        # Test exponential weighted moving average
        assert ewma(100.0, None) == 100.0  # No previous value
        assert ewma(100.0, 90.0, 0.4) == 94.0  # 0.4 * 100 + 0.6 * 90 = 40 + 54 = 94

    def test_estimate_basic(self):
        prices_now = {"Nairobi": 100.0, "Nakuru": 90.0}
        distances = {"Nairobi": 0.0, "Nakuru": 50.0}
        
        estimate_value, confidence_band, explain = estimate(
            prices_now=prices_now,
            distances=distances,
            prev_base=None,
            season_index=0.0,
            logistics_mode="wholesale",
            shock_index=0.0,
            variety_grade_factor=1.0,
            weather_index=0.0
        )
        
        assert isinstance(estimate_value, float)
        assert len(confidence_band) == 2
        assert confidence_band[0] < estimate_value < confidence_band[1]
        assert isinstance(explain, dict)
        assert "base_smoothed" in explain
        assert explain["logistics_mult"] == 1.0  # wholesale

    def test_estimate_with_weather(self):
        prices_now = {"Nairobi": 100.0}
        distances = {"Nairobi": 0.0}
        
        # Test with high weather index (adverse weather)
        estimate_high_weather, _, explain_high = estimate(
            prices_now=prices_now,
            distances=distances,
            prev_base=None,
            weather_index=1.0  # Maximum weather impact
        )
        
        # Test with no weather impact
        estimate_normal, _, explain_normal = estimate(
            prices_now=prices_now,
            distances=distances,
            prev_base=None,
            weather_index=0.0
        )
        
        # High weather should increase price
        assert estimate_high_weather > estimate_normal
        assert explain_high["weather_mult"] > explain_normal["weather_mult"]

    def test_logistics_modes(self):
        prices_now = {"Nairobi": 100.0}
        distances = {"Nairobi": 0.0}
        
        farmgate, _, explain_fg = estimate(prices_now, distances, None, logistics_mode="farmgate")
        wholesale, _, explain_ws = estimate(prices_now, distances, None, logistics_mode="wholesale")
        retail, _, explain_rt = estimate(prices_now, distances, None, logistics_mode="retail")
        
        # Farmgate < Wholesale < Retail
        assert farmgate < wholesale < retail
        assert explain_fg["logistics_mult"] == 0.90
        assert explain_ws["logistics_mult"] == 1.00
        assert explain_rt["logistics_mult"] == 1.20

    def test_season_impact(self):
        prices_now = {"Nairobi": 100.0}
        distances = {"Nairobi": 0.0}
        
        # Negative season index (abundant season)
        abundant, _, explain_abundant = estimate(prices_now, distances, None, season_index=-0.5)
        
        # Positive season index (scarce season)
        scarce, _, explain_scarce = estimate(prices_now, distances, None, season_index=0.5)
        
        # Scarce season should have higher prices
        assert scarce > abundant
        assert explain_scarce["season_mult"] > explain_abundant["season_mult"]