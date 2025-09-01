# 🥔 Potato Price Estimation Algorithm

## Overview

The Potato Price API uses a **hybrid rule-statistical approach** that combines market data, weather conditions, and contextual factors to produce transparent, explainable price estimates. The algorithm is designed to be simple, interpretable, and easily replaceable with more sophisticated ML models in the future.

## 🎯 Design Principles

- **Explainable**: Every price component can be traced and understood
- **Context-Aware**: Incorporates multiple factors affecting potato pricing
- **Adaptive**: Uses exponential weighted moving averages for dynamic baseline
- **Robust**: Handles missing data and provides uncertainty estimates
- **Extensible**: Pure function design allows easy model replacement

---

## 📊 Algorithm Overview

```
Market Prices → Distance Weighting → EWMA Smoothing → Context Multipliers → Final Estimate
     ↓               ↓                    ↓                    ↓               ↓
  [P₁,P₂,P₃]    [w₁,w₂,w₃]         base_smoothed        [season,logistics,   p_hat ± σ
                                                         shock,weather,
                                                         variety]
```

### Core Formula

```
p_hat = base_smoothed × adj_season × adj_logistics × adj_shock × adj_weather × variety_grade_factor
```

---

## 🔢 Step-by-Step Calculation

### Step 1: Distance-Weighted Base Price

**Purpose**: Combine nearby market prices weighted by proximity/friction

```python
# Calculate weights based on distance/friction
w[m] = 1 / (1 + dist(target, m))

# Weighted average of market prices
p_base_raw = Σ(w[m] × price[m]) / Σ(w[m])
```

**Example**:
- Market prices: Nairobi=100, Nakuru=90, Nyeri=95 KES/kg
- Distances to Nyandarua: Nairobi=100km, Nakuru=80km, Nyeri=60km
- Weights: w_Nairobi=0.010, w_Nakuru=0.012, w_Nyeri=0.016
- Base price: (100×0.010 + 90×0.012 + 95×0.016) / (0.010+0.012+0.016) = 94.7 KES/kg

### Step 2: Exponential Weighted Moving Average (EWMA)

**Purpose**: Smooth price fluctuations and maintain historical context

```python
# EWMA with smoothing parameter α (default: 0.4)
base_smoothed = α × p_base_raw + (1-α) × prev_base

# If no previous base exists
if prev_base is None:
    base_smoothed = p_base_raw
```

**Benefits**:
- Reduces volatility from single-day price spikes
- Maintains price momentum and trends
- Automatically adapts to structural price changes

### Step 3: Context Multipliers

#### 3.1 Seasonal Adjustment

**Purpose**: Account for seasonal supply/demand patterns

```python
adj_season = 1 + k1 × season_index
```

- **season_index** ∈ [-1, 1]: -1 (abundant harvest) to +1 (scarcity)
- **k1** (sensitivity): 0.12 (12% max seasonal impact)
- **Example**: season_index=0.5 → adj_season=1.06 (6% price increase)

#### 3.2 Logistics Mode Adjustment

**Purpose**: Reflect different supply chain stages

```python
logistics_multipliers = {
    "farmgate": 0.90,    # Farm-gate prices (before transportation)
    "wholesale": 1.00,   # Wholesale market prices (baseline)
    "retail": 1.20       # Consumer retail prices
}
adj_logistics = logistics_multipliers[logistics_mode]
```

#### 3.3 Market Shock Adjustment

**Purpose**: Capture extraordinary market events

```python
adj_shock = 1 + k2 × shock_index
```

- **shock_index** ∈ [-1, 1]: Market disruption severity
- **k2** (sensitivity): 0.08 (8% max shock impact)
- **Examples**: Transport strike (+0.3), bumper harvest (-0.4)

#### 3.4 Weather Impact Adjustment

**Purpose**: Incorporate weather effects on supply and demand

```python
adj_weather = 1 + k3 × weather_index
```

- **weather_index** ∈ [0, 1]: Derived from rainfall, temperature
- **k3** (sensitivity): 0.12 (12% max weather impact)

**Weather Index Calculation**:
```python
# Rain impact (mm/day)
weather_index = min(1.0, rain_mm / 30.0)

# Heavy rain (>10mm) → index ~0.3+
# Extreme rain (>30mm) → index ~1.0
```

#### 3.5 Variety/Grade Quality Factor

**Purpose**: Adjust for potato quality and variety

```python
# Direct multiplier (no additional sensitivity parameter)
# Range: [0.5, 2.0] validated by API
variety_mult = variety_grade_factor
```

**Examples**:
- Premium seed potatoes: 1.5 (50% premium)
- Standard table grade: 1.0 (baseline)
- Processing grade: 0.7 (30% discount)

### Step 4: Final Price Calculation

```python
p_hat = base_smoothed × adj_season × adj_logistics × adj_shock × adj_weather × variety_grade_factor
```

### Step 5: Uncertainty Band

**Purpose**: Provide confidence intervals based on historical volatility

```python
# Dynamic sigma from historical residuals (preferred)
sigma = model_state['sigma:{location}'] 

# Fallback: scale-based estimate
if sigma is None:
    sigma = max(0.5, 0.03 × p_hat)

# Confidence band (±1 standard deviation)
confidence_band = [p_hat - sigma, p_hat + sigma]
```

---

## 📈 Parameter Sensitivity Analysis

| Parameter        | Default | Range     | Max Impact | Use Case                 |
| ---------------- | ------- | --------- | ---------- | ------------------------ |
| **k1** (season)  | 0.12    | 0.05-0.20 | ±20%       | Seasonal supply cycles   |
| **k2** (shock)   | 0.08    | 0.05-0.15 | ±15%       | Market disruptions       |
| **k3** (weather) | 0.12    | 0.08-0.18 | ±18%       | Weather events           |
| **α** (EWMA)     | 0.4     | 0.2-0.6   | Smoothing  | Price volatility control |

---

## 🔬 Scientific Rationale

### 1. Distance-Weighted Base
- **Theory**: Spatial price integration theory - closer markets have stronger price correlation
- **Implementation**: Inverse distance weighting with friction adjustments
- **Data Source**: Precomputed friction maps considering transport costs, infrastructure

### 2. EWMA Smoothing
- **Theory**: Financial time series analysis - recent prices more predictive than distant ones
- **Implementation**: Exponential decay with configurable half-life
- **Benefits**: Trend following while filtering noise

### 3. Multiplicative Model
- **Theory**: Economic factors interact multiplicatively rather than additively
- **Implementation**: Independent multipliers for each context factor
- **Advantage**: Interpretable component contributions

### 4. Weather Integration
- **Theory**: Agricultural economics - weather affects both supply (production) and demand (storage needs)
- **Implementation**: Rainfall-based index with saturation effects
- **Enhancement**: Future versions can incorporate temperature, humidity, evapotranspiration

---

## 🧮 Worked Example

### Input Parameters
```json
{
  "location": "Nyandarua",
  "logistics_mode": "wholesale",
  "variety_grade_factor": 1.0,
  "season_index": 0.2,
  "shock_index": 0.0,
  "weather_override": null
}
```

### Market Data
```json
{
  "market_prices": {"Nairobi": 100, "Nakuru": 90, "Nyeri": 95},
  "distances": {"Nairobi": 100, "Nakuru": 80, "Nyeri": 60},
  "prev_base": 92.5,
  "weather_index": 0.3
}
```

### Calculation Steps
```python
# Step 1: Distance weights
w = {"Nairobi": 1/101=0.0099, "Nakuru": 1/81=0.0123, "Nyeri": 1/61=0.0164}
total_weight = 0.0386

# Step 2: Weighted average
p_base_raw = (100×0.0099 + 90×0.0123 + 95×0.0164) / 0.0386 = 94.68

# Step 3: EWMA smoothing
base_smoothed = 0.4 × 94.68 + 0.6 × 92.5 = 93.37

# Step 4: Context multipliers
adj_season = 1 + 0.12 × 0.2 = 1.024
adj_logistics = 1.0 (wholesale)
adj_shock = 1 + 0.08 × 0.0 = 1.0
adj_weather = 1 + 0.12 × 0.3 = 1.036
variety_mult = 1.0

# Step 5: Final calculation
p_hat = 93.37 × 1.024 × 1.0 × 1.0 × 1.036 × 1.0 = 99.13

# Step 6: Uncertainty (assuming σ=2.5)
confidence_band = [96.63, 101.63]
```

### Output
```json
{
  "estimate": 99.13,
  "range": [96.63, 101.63],
  "explain": {
    "base_smoothed": 93.37,
    "season_mult": 1.024,
    "logistics_mult": 1.0,
    "shock_mult": 1.0,
    "weather_mult": 1.036,
    "variety_mult": 1.0
  }
}
```

---

## 🔧 Model Calibration

### Parameter Tuning
Parameters are calibrated using historical price data and cross-validation:

1. **Sensitivity Parameters (k1, k2, k3)**: Optimized to minimize RMSE on held-out data
2. **EWMA Alpha**: Chosen to balance responsiveness vs. stability
3. **Distance Friction**: Derived from transportation cost analysis

### Validation Methodology
- **Backtesting**: Rolling window validation on 2+ years historical data
- **Cross-Market**: Validate model performance across different markets
- **Seasonal Splits**: Ensure model works across harvest and non-harvest periods

---

## 🚀 Future Enhancements

### Short-term (3-6 months)
1. **Enhanced Weather Model**: Temperature, humidity, soil moisture integration
2. **Transport Cost Integration**: Real-time fuel prices, road conditions
3. **Market Sentiment**: News analysis, trader sentiment indicators

### Medium-term (6-12 months)
1. **Machine Learning Hybrid**: Ensemble of rule-based + ML models
2. **Multi-commodity**: Extend to other crops with cross-commodity effects
3. **Demand Modeling**: Population, income, substitute goods integration

### Long-term (12+ months)
1. **Deep Learning**: LSTM/Transformer models for complex pattern recognition
2. **Satellite Integration**: Crop monitoring, yield forecasting
3. **Market Microstructure**: Order book analysis, trading volume effects

---

## 📚 References & Further Reading

### Academic Sources
1. Fackler, P.L. & Goodwin, B.K. (2001). "Spatial price analysis." *Handbook of Agricultural Economics*
2. Rapsomanikis, G. & Mugera, H. (2006). "Spatial integration and price transmission in domestic rice markets." *FAO Working Paper*
3. Meyer, J. & von Cramon-Taubadel, S. (2004). "Asymmetric price transmission: A survey." *Journal of Agricultural Economics*

### Technical Implementation
1. **Exponential Smoothing**: Hyndman, R.J. & Athanasopoulos, G. "Forecasting: Principles and Practice"
2. **Spatial Economics**: Anselin, L. "Spatial Econometrics: Methods and Models"
3. **Agricultural Price Analysis**: Tomek, W.G. & Kaiser, H.M. "Agricultural Product Prices"

### Data Sources
- **Market Prices**: Kenya Agricultural Market Information System (KAMIS)
- **Weather Data**: OpenWeatherMap API, Kenya Meteorological Department
- **Transport Costs**: Kenya Bureau of Statistics, Ministry of Transport

---

## 💡 Implementation Notes

### Code Organization
- **Core Algorithm**: `api/app/estimator.py` - Pure function implementation
- **Parameter Storage**: `model_state` table for dynamic parameters
- **Validation**: Pydantic schemas ensure input constraints
- **Caching**: Redis caches computed estimates for 5 minutes

### Testing Strategy
- **Unit Tests**: `tests/test_estimator.py` - Algorithm component testing
- **Integration Tests**: End-to-end price estimation workflows
- **Performance Tests**: Latency and throughput validation

### Monitoring
- **Residual Tracking**: Automated computation of prediction errors
- **Parameter Drift**: Monitor for parameter instability
- **Data Quality**: Validate input data ranges and consistency

---

*This algorithm serves as the foundation for context-aware potato price estimation in Kenya. The modular design allows for continuous improvement while maintaining explainability and reliability.*
