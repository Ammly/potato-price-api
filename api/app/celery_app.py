import os
from celery import Celery

def make_celery(app=None):
    celery = Celery(
        'potato_price_api',
        broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
        include=['app.tasks']
    )
    
    celery.conf.update(
        task_serializer='json',
        accept_content=['json'],
        result_serializer='json',
        timezone='UTC',
        enable_utc=True,
        beat_schedule={
            'fetch-weather-data': {
                'task': 'app.tasks.fetch_weather_data',
                'schedule': 3600.0,  # Every hour
            },
            'compute-price-residuals': {
                'task': 'app.tasks.compute_price_residuals',
                'schedule': 86400.0,  # Every day
            },
            'cleanup-old-weather': {
                'task': 'app.tasks.clear_old_weather_data',
                'schedule': 604800.0,  # Every week
            },
        },
    )
    
    if app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

# Create standalone celery instance for worker
celery_app = make_celery()