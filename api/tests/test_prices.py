# api/tests/test_prices.py
import pytest
import json
from datetime import datetime, timezone
from unittest.mock import patch
from app.main import create_app
from app.extensions import db
from app.models import User, Market, MarketPrice, ModelState
from app.utils.jwt_utils import create_access_token

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_token(app):
    with app.app_context():
        user = User(username='testuser', password_hash='dummy')
        db.session.add(user)
        db.session.commit()
        token = create_access_token(sub=user.id)
        return token

@pytest.fixture
def sample_data(app):
    with app.app_context():
        # Create markets
        markets = [
            Market(name='Nairobi', lat=-1.2921, lon=36.8219),
            Market(name='Nakuru', lat=-0.3031, lon=36.0800),
            Market(name='Nyeri', lat=-0.4167, lon=36.9500)
        ]
        for market in markets:
            db.session.add(market)
        db.session.commit()
        
        # Create sample prices
        from datetime import datetime, timezone
        prices = [
            MarketPrice(market_id=1, date=datetime.now(timezone.utc), price_kg=100.0, source='test'),
            MarketPrice(market_id=2, date=datetime.now(timezone.utc), price_kg=90.0, source='test'),
            MarketPrice(market_id=3, date=datetime.now(timezone.utc), price_kg=95.0, source='test'),
        ]
        for price in prices:
            db.session.add(price)
        db.session.commit()

class TestPrices:
    def test_estimate_unauthorized(self, client):
        response = client.post('/prices/estimate',
                             data=json.dumps({
                                 'location': 'Nairobi',
                                 'logistics_mode': 'wholesale'
                             }),
                             content_type='application/json')
        
        assert response.status_code == 401

    def test_estimate_invalid_token(self, client):
        response = client.post('/prices/estimate',
                             data=json.dumps({
                                 'location': 'Nairobi',
                                 'logistics_mode': 'wholesale'
                             }),
                             content_type='application/json',
                             headers={'Authorization': 'Bearer invalid-token'})
        
        assert response.status_code == 401

    def test_estimate_success(self, client, auth_token, sample_data):
        response = client.post('/prices/estimate',
                             data=json.dumps({
                                 'location': 'Nairobi',
                                 'logistics_mode': 'wholesale',
                                 'variety_grade_factor': 1.0,
                                 'season_index': 0.0,
                                 'shock_index': 0.0
                             }),
                             content_type='application/json',
                             headers={'Authorization': f'Bearer {auth_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'estimate' in data
        assert 'range' in data
        assert 'explain' in data
        assert 'sources' in data
        assert data['units'] == 'KES/kg'
        assert len(data['range']) == 2
        assert data['range'][0] < data['estimate'] < data['range'][1]

    def test_estimate_with_overrides(self, client, auth_token, sample_data):
        response = client.post('/prices/estimate',
                             data=json.dumps({
                                 'location': 'Nairobi',
                                 'logistics_mode': 'retail',
                                 'variety_grade_factor': 1.2,
                                 'overrides': {
                                     'Nairobi': 120.0,
                                     'Nakuru': 110.0
                                 }
                             }),
                             content_type='application/json',
                             headers={'Authorization': f'Bearer {auth_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Retail should have higher multiplier than wholesale
        assert data['explain']['logistics_mult'] == 1.20
        assert data['explain']['variety_mult'] == 1.2

    def test_estimate_invalid_logistics_mode(self, client, auth_token):
        response = client.post('/prices/estimate',
                             data=json.dumps({
                                 'location': 'Nairobi',
                                 'logistics_mode': 'invalid_mode'
                             }),
                             content_type='application/json',
                             headers={'Authorization': f'Bearer {auth_token}'})
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'invalid_payload'

    def test_markets_endpoint_empty(self, client):
        """Test markets endpoint with no markets in database"""
        response = client.get('/prices/markets')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'markets' in data
        assert data['count'] == 0
        assert len(data['markets']) == 0

    def test_markets_endpoint_with_data(self, client, app):
        """Test markets endpoint with sample market data"""
        with app.app_context():
            # Create a sample market
            market = Market(name='Nairobi', lat=-1.2921, lon=36.8219, county='Nairobi')
            db.session.add(market)
            db.session.commit()
            
            # Add a sample price
            price = MarketPrice(
                market_id=market.id,
                date=datetime.now(timezone.utc),
                price_kg=95.0,
                source='test'
            )
            db.session.add(price)
            db.session.commit()
        
        response = client.get('/prices/markets')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['count'] == 1
        assert len(data['markets']) == 1
        
        market_data = data['markets'][0]
        assert market_data['name'] == 'Nairobi'
        assert market_data['county'] == 'Nairobi'
        assert market_data['latest_price']['price_kg'] == 95.0

    def test_estimate_weather_override(self, client, auth_token, sample_data):
        response = client.post('/prices/estimate',
                             data=json.dumps({
                                 'location': 'Nairobi',
                                 'logistics_mode': 'wholesale',
                                 'weather_override': 0.8
                             }),
                             content_type='application/json',
                             headers={'Authorization': f'Bearer {auth_token}'})
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Weather impact should be reflected in the multiplier
        assert data['explain']['weather_mult'] > 1.0
