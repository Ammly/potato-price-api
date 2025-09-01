# api/tests/conftest.py
import pytest
import os
import tempfile
import warnings
from app.main import create_app
from app.extensions import db

# Set test environment variables
os.environ['JWT_SECRET'] = 'test-jwt-secret'
os.environ['SECRET_KEY'] = 'test-flask-secret'
os.environ['WEATHER_API_KEY'] = 'test-weather-key'

# Suppress warnings at the system level
os.environ['PYTHONWARNINGS'] = 'ignore::DeprecationWarning,ignore::UserWarning'

# Suppress all warnings during tests
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=ImportWarning)

# Configure pytest to suppress specific deprecation warnings
@pytest.fixture(autouse=True)
def suppress_warnings():
    """Suppress expected deprecation warnings in tests"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        yield

@pytest.fixture(scope='session')
def app():
    """Create application for the tests."""
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()
