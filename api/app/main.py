# api/app/main.py
import os
from flask import Flask
from .extensions import db, migrate, limiter
from .auth import auth_bp
from .prices import prices_bp
from .weather import weather_bp
from .config import config

def create_app(config_name=None):
    app = Flask(__name__)
    
    # Load configuration
    config_name = config_name or os.getenv('FLASK_ENV', 'development')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure rate limiter - skip initialization in testing to avoid warnings
    if not app.config.get('TESTING'):
        # Configure rate limiter with storage if available
        storage_url = app.config.get('RATELIMIT_STORAGE_URL')
        if storage_url:
            try:
                limiter.init_app(app, storage_uri=storage_url)
            except Exception:
                # Fallback to in-memory if Redis is not available
                limiter.init_app(app)
        else:
            limiter.init_app(app)
    else:
        # In testing mode, create a mock limiter that does nothing
        class MockLimiter:
            def limit(self, *args, **kwargs):
                def decorator(f):
                    return f
                return decorator
        
        import sys
        sys.modules[__name__].limiter = MockLimiter()
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(prices_bp, url_prefix='/prices')
    app.register_blueprint(weather_bp, url_prefix='/weather')
    
    @app.route('/health')
    def health():
        """Enhanced health check with DB and Redis connectivity"""
        from datetime import datetime
        health_status = {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "services": {}
        }
        
        # Check database connectivity
        try:
            from sqlalchemy import text
            db.session.execute(text("SELECT 1"))
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Redis connectivity
        try:
            from .extensions import get_redis
            redis_client = get_redis()
            redis_client.ping()
            health_status["services"]["redis"] = "healthy"
        except Exception as e:
            health_status["services"]["redis"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "ok" else 503
        return health_status, status_code
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0')