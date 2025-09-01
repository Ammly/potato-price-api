import json
import hashlib
from flask import Blueprint, request, jsonify
from .schemas import EstimateRequest, EstimateResponse
from .decorators import jwt_required
from .extensions import db, get_redis, limiter
from .models import Market, MarketPrice, WeatherData, ModelState
from .estimator import estimate as estimator_fn

prices_bp = Blueprint("prices", __name__)

def get_cache_key(req_data):
    """Generate cache key from request parameters"""
    # Sort the dict to ensure consistent hashing
    normalized = json.dumps(req_data, sort_keys=True)
    return f"estimate:{hashlib.md5(normalized.encode()).hexdigest()}"

@prices_bp.route("/estimate", methods=["POST"])
@jwt_required
@limiter.limit("120 per minute")  # Rate limit price estimates
def estimate_price():
    body = request.get_json()
    try:
        req = EstimateRequest.model_validate(body)
    except Exception as e:
        return jsonify({"error": "invalid_payload", "details": str(e)}), 400

    # Check Redis cache first
    redis_client = get_redis()
    cache_key = get_cache_key(body)
    
    try:
        cached_result = redis_client.get(cache_key)
        if cached_result:
            return jsonify(json.loads(cached_result)), 200
    except Exception:
        pass  # Continue if cache fails

    # 1) Resolve markets nearby — for now: use a hard-coded set: Nairobi, Nakuru, Nyeri
    # In production: query Market table for nearby markets to req.location
    markets = ["Nairobi", "Nakuru", "Nyeri"]

    # 2) Get latest prices either from overrides or DB
    prices_now = {}
    distances = {}
    for m in markets:
        if req.overrides and m in req.overrides:
            prices_now[m] = float(req.overrides[m])
        else:
            # get latest market price
            mp = (db.session.query(MarketPrice)
                  .join(Market, Market.id == MarketPrice.market_id)
                  .filter(Market.name == m)
                  .order_by(MarketPrice.date.desc())
                  .first())
            prices_now[m] = mp.price_kg if mp else 0.0

        # friction map / distance — try to get from Market.friction_map
        market = db.session.query(Market).filter_by(name=m).first()
        if market and market.friction_map:
            distances[m] = market.friction_map.get(req.location, 100.0)
        else:
            # fallback static distances (placeholder)
            distances[m] = 100.0 if m == "Nairobi" else 80.0 if m == "Nakuru" else 60.0

    # 3) get prev_base from ModelState
    prev_base = None
    state = db.session.query(ModelState).filter_by(key=f"base:{req.location}").first()
    if state:
        prev_base = state.value.get("base")

    # 4) weather_index: use override or latest WeatherData for the target location (if exists)
    weather_index = req.weather_override if req.weather_override is not None else 0.0
    
    # Try Redis cache first for weather
    try:
        cached_weather = redis_client.get(f"weather:latest:{req.location}")
        if cached_weather:
            weather_data = json.loads(cached_weather)
            weather_index = weather_data.get('weather_index', 0.0)
    except Exception:
        # Fallback to database
        w = (db.session.query(WeatherData)
             .join(Market, Market.id == WeatherData.market_id)
             .filter(Market.name == req.location)
             .order_by(WeatherData.timestamp.desc())
             .first())
        if w:
            weather_index = w.weather_index

    # 5) Get dynamic sigma from cache or database
    sigma = 1.0  # default fallback
    try:
        cached_sigma = redis_client.get(f"sigma:{req.location}")
        if cached_sigma:
            sigma_data = json.loads(cached_sigma)
            sigma = sigma_data.get('sigma', 1.0)
    except Exception:
        # Fallback to database
        sigma_state = db.session.query(ModelState).filter_by(key=f"sigma:{req.location}").first()
        if sigma_state:
            sigma = sigma_state.value.get("sigma", 1.0)

    # 6) compute estimate
    p_hat, band, explain = estimator_fn(
        prices_now=prices_now,
        distances=distances,
        prev_base=prev_base,
        season_index=req.season_index or 0.0,
        logistics_mode=req.logistics_mode,
        shock_index=req.shock_index or 0.0,
        variety_grade_factor=req.variety_grade_factor,
        weather_index=weather_index,
    )

    # Use dynamic sigma for confidence band
    confidence_band = [float(p_hat - sigma), float(p_hat + sigma)]

    # 7) persist new base into model state
    db_state = db.session.query(ModelState).filter_by(key=f"base:{req.location}").first()
    if db_state:
        db_state.value = {"base": explain["base_smoothed"]}
    else:
        db_state = ModelState(key=f"base:{req.location}", value={"base": explain["base_smoothed"]})
        db.session.add(db_state)
    db.session.commit()

    resp = EstimateResponse(
        estimate=round(p_hat, 2),
        range=[round(confidence_band[0], 2), round(confidence_band[1], 2)],
        explain=explain,
        sources=["KAMIS/NPCK (db)"]
    )

    # Cache the result for 5 minutes
    result_json = resp.model_dump()
    try:
        redis_client.setex(cache_key, 300, json.dumps(result_json))
    except Exception:
        pass  # Continue if cache fails

    return jsonify(result_json), 200

@prices_bp.route("/markets", methods=["GET"])
def list_markets():
    """Get list of all markets with latest prices"""
    try:
        markets = db.session.query(Market).all()
        result = []
        
        for market in markets:
            # Get latest price for this market
            latest_price = (db.session.query(MarketPrice)
                           .filter(MarketPrice.market_id == market.id)
                           .order_by(MarketPrice.date.desc())
                           .first())
            
            market_data = {
                "id": market.id,
                "name": market.name,
                "county": market.county,
                "lat": market.lat,
                "lon": market.lon,
                "latest_price": {
                    "price_kg": latest_price.price_kg if latest_price else None,
                    "date": latest_price.date.isoformat() if latest_price else None,
                    "source": latest_price.source if latest_price else None
                } if latest_price else None
            }
            result.append(market_data)
        
        return jsonify({
            "markets": result,
            "count": len(result)
        }), 200
        
    except Exception as e:
        return jsonify({"error": "internal_error", "details": str(e)}), 500