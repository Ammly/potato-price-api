# api/app/weather.py
import json
from flask import Blueprint, request, jsonify, current_app
from .extensions import db, get_redis, limiter
from .models import Market, WeatherData
from .services.weather_fetcher import fetch_weather_for
from datetime import datetime, timedelta

weather_bp = Blueprint("weather", __name__)

@weather_bp.route("/latest", methods=["GET"])
@limiter.limit("60 per minute")  # Rate limit weather requests
def latest_weather():
    location = request.args.get("location")
    if not location:
        return jsonify({"error": "missing_location"}), 400

    # Try Redis cache first
    redis_client = get_redis()
    try:
        cached_weather = redis_client.get(f"weather:latest:{location}")
        if cached_weather:
            weather_data = json.loads(cached_weather)
            return jsonify({
                "timestamp": weather_data["timestamp"],
                "rain_mm": weather_data["rain_mm"],
                "weather_index": weather_data["weather_index"],
                "weather_code": weather_data["weather_code"],
                "source": "cache"
            }), 200
    except Exception:
        pass  # Continue to database/API fallback

    m = db.session.query(Market).filter_by(name=location).first()
    if not m:
        return jsonify({"error": "unknown_location"}), 404

    # return latest weather data from database
    w = (db.session.query(WeatherData)
         .filter(WeatherData.market_id == m.id)
         .order_by(WeatherData.timestamp.desc())
         .first())
    if not w:
        # fetch on demand (synchronous) — uses OpenWeatherMap; careful with rate limits
        try:
            payload = fetch_weather_for(m.lat, m.lon, current_app.config["WEATHER_API_KEY"])
            wd = WeatherData(market_id=m.id,
                             timestamp=datetime.utcnow(),
                             rain_mm=payload["rain_mm"],
                             weather_code=str(payload["weather_code"]),
                             weather_index=float(payload["weather_index"]),
                             raw=payload)
            db.session.add(wd)
            db.session.commit()
            
            # Cache the fresh data
            cache_data = {
                'timestamp': payload['timestamp'],
                'rain_mm': payload['rain_mm'],
                'weather_index': payload['weather_index'],
                'weather_code': payload['weather_code']
            }
            try:
                redis_client.setex(f"weather:latest:{location}", 7200, json.dumps(cache_data))
            except Exception:
                pass
            
            return jsonify({"weather": payload, "source": "api"}), 200
        except Exception as e:
            return jsonify({"error": "fetch_error", "details": str(e)}), 500

    return jsonify({
        "timestamp": w.timestamp.isoformat(),
        "rain_mm": w.rain_mm,
        "weather_index": w.weather_index,
        "weather_code": w.weather_code,
        "raw": w.raw,
        "source": "database"
    }), 200

@weather_bp.route("/history", methods=["GET"])
@limiter.limit("30 per minute")
def weather_history():
    """Get historical weather data for a location"""
    location = request.args.get("location")
    days = int(request.args.get("days", 7))  # Default 7 days
    
    if not location:
        return jsonify({"error": "missing_location"}), 400
    
    if days > 30:
        return jsonify({"error": "max_30_days"}), 400

    m = db.session.query(Market).filter_by(name=location).first()
    if not m:
        return jsonify({"error": "unknown_location"}), 404

    # Get historical weather data
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    weather_records = (db.session.query(WeatherData)
                      .filter(WeatherData.market_id == m.id)
                      .filter(WeatherData.timestamp >= cutoff_date)
                      .order_by(WeatherData.timestamp.desc())
                      .limit(days * 4)  # Allow for multiple records per day
                      .all())

    history = []
    for record in weather_records:
        history.append({
            "timestamp": record.timestamp.isoformat(),
            "rain_mm": record.rain_mm,
            "weather_index": record.weather_index,
            "weather_code": record.weather_code
        })

    return jsonify({
        "location": location,
        "days_requested": days,
        "records_found": len(history),
        "history": history
    }), 200