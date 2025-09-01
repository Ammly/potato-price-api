# api/app/tasks.py
import os
import json
import numpy as np
from .celery_app import celery_app
from .extensions import db, get_redis
from .models import Market, WeatherData, MarketPrice, ModelState
from .services.weather_fetcher import fetch_weather_for
from .estimator import estimate as estimator_fn
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def fetch_weather_data():
    """
    Periodic task to fetch weather data for all markets
    """
    try:
        markets = db.session.query(Market).filter(Market.lat.isnot(None), Market.lon.isnot(None)).all()
        updated_count = 0
        
        for market in markets:
            try:
                # Fetch weather data from OpenWeatherMap
                weather_payload = fetch_weather_for(
                    market.lat, 
                    market.lon, 
                    os.getenv('WEATHER_API_KEY')
                )
                
                # Store in database
                weather_data = WeatherData(
                    market_id=market.id,
                    timestamp=datetime.utcnow(),
                    rain_mm=weather_payload['rain_mm'],
                    weather_code=str(weather_payload['weather_code']),
                    weather_index=weather_payload['weather_index'],
                    raw=weather_payload
                )
                
                db.session.add(weather_data)
                
                # Cache latest weather in Redis for fast access
                redis_client = get_redis()
                cache_key = f"weather:latest:{market.name}"
                cache_data = {
                    'timestamp': weather_payload['timestamp'],
                    'rain_mm': weather_payload['rain_mm'],
                    'weather_index': weather_payload['weather_index'],
                    'weather_code': weather_payload['weather_code']
                }
                redis_client.setex(cache_key, 7200, json.dumps(cache_data))  # 2 hour TTL
                
                updated_count += 1
                logger.info(f"Fetched weather data for market {market.name}")
                
            except Exception as e:
                logger.error(f"Failed to fetch weather for market {market.name}: {str(e)}")
                continue
        
        db.session.commit()
        logger.info(f"Successfully updated weather data for {updated_count}/{len(markets)} markets")
        return {'updated_markets': updated_count, 'total_markets': len(markets)}
        
    except Exception as e:
        logger.error(f"Failed to fetch weather data: {str(e)}")
        db.session.rollback()
        raise

@celery_app.task
def compute_price_residuals():
    """
    Periodic task to compute price residuals and update model sigma for all locations
    """
    try:
        locations = ['Nairobi', 'Nakuru', 'Nyeri', 'Mombasa', 'Eldoret']
        updated_sigmas = {}
        
        for location in locations:
            try:
                # Get recent price data (last 30 days)
                cutoff_date = datetime.utcnow() - timedelta(days=30)
                
                # Get actual prices
                actual_prices = []
                estimated_prices = []
                
                # Query market prices for this location and nearby markets
                markets = ['Nairobi', 'Nakuru', 'Nyeri']  # Core markets for estimation
                
                for days_ago in range(1, 31):  # Last 30 days
                    price_date = datetime.utcnow() - timedelta(days=days_ago)
                    
                    # Get actual price for the location on this date
                    market = db.session.query(Market).filter_by(name=location).first()
                    if not market:
                        continue
                        
                    actual_price_record = (db.session.query(MarketPrice)
                                         .filter(MarketPrice.market_id == market.id)
                                         .filter(MarketPrice.date >= price_date.date())
                                         .filter(MarketPrice.date < (price_date + timedelta(days=1)).date())
                                         .first())
                    
                    if not actual_price_record:
                        continue
                        
                    # Get market prices for estimation
                    prices_now = {}
                    distances = {'Nairobi': 100, 'Nakuru': 80, 'Nyeri': 60}  # Simplified
                    
                    for m in markets:
                        mp = (db.session.query(MarketPrice)
                              .join(Market, Market.id == MarketPrice.market_id)
                              .filter(Market.name == m)
                              .filter(MarketPrice.date >= price_date.date())
                              .filter(MarketPrice.date < (price_date + timedelta(days=1)).date())
                              .first())
                        if mp:
                            prices_now[m] = mp.price_kg
                    
                    if len(prices_now) < 2:  # Need at least 2 market prices
                        continue
                    
                    # Get weather data for this date
                    weather_data = (db.session.query(WeatherData)
                                  .filter(WeatherData.market_id == market.id)
                                  .filter(WeatherData.timestamp >= price_date)
                                  .filter(WeatherData.timestamp < price_date + timedelta(days=1))
                                  .first())
                    
                    weather_index = weather_data.weather_index if weather_data else 0.0
                    
                    # Get previous base
                    prev_base = None
                    state = db.session.query(ModelState).filter_by(key=f"base:{location}").first()
                    if state:
                        prev_base = state.value.get("base")
                    
                    # Compute estimate
                    try:
                        p_hat, _, _ = estimator_fn(
                            prices_now=prices_now,
                            distances=distances,
                            prev_base=prev_base,
                            weather_index=weather_index
                        )
                        
                        actual_prices.append(actual_price_record.price_kg)
                        estimated_prices.append(p_hat)
                        
                    except Exception as e:
                        logger.warning(f"Failed to compute estimate for {location} on {price_date}: {e}")
                        continue
                
                # Compute residual standard deviation
                if len(actual_prices) >= 10:  # Need sufficient data
                    residuals = np.array(actual_prices) - np.array(estimated_prices)
                    sigma = float(np.std(residuals))
                    
                    # Store sigma in ModelState
                    sigma_state = db.session.query(ModelState).filter_by(key=f"sigma:{location}").first()
                    if sigma_state:
                        sigma_state.value = {"sigma": sigma, "last_updated": datetime.utcnow().isoformat()}
                    else:
                        sigma_state = ModelState(
                            key=f"sigma:{location}", 
                            value={"sigma": sigma, "last_updated": datetime.utcnow().isoformat()}
                        )
                        db.session.add(sigma_state)
                    
                    # Cache in Redis
                    redis_client = get_redis()
                    redis_client.setex(f"sigma:{location}", 86400, json.dumps({"sigma": sigma}))  # 24h TTL
                    
                    updated_sigmas[location] = sigma
                    logger.info(f"Updated sigma for {location}: {sigma:.3f}")
                else:
                    logger.warning(f"Insufficient data for {location}: {len(actual_prices)} samples")
                    
            except Exception as e:
                logger.error(f"Failed to compute sigma for {location}: {str(e)}")
                continue
        
        db.session.commit()
        logger.info(f"Successfully updated sigma for {len(updated_sigmas)} locations")
        return {'updated_locations': list(updated_sigmas.keys()), 'sigmas': updated_sigmas}
        
    except Exception as e:
        logger.error(f"Failed to compute price residuals: {str(e)}")
        db.session.rollback()
        raise

@celery_app.task
def clear_old_weather_data():
    """
    Cleanup task to remove weather data older than 90 days
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=90)
        
        deleted_count = (db.session.query(WeatherData)
                        .filter(WeatherData.timestamp < cutoff_date)
                        .delete())
        
        db.session.commit()
        logger.info(f"Cleaned up {deleted_count} old weather records")
        return {'deleted_records': deleted_count}
        
    except Exception as e:
        logger.error(f"Failed to cleanup old weather data: {str(e)}")
        db.session.rollback()
        raise
