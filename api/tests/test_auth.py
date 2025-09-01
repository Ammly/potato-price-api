import pytest
import json
from app.main import create_app
from app.extensions import db
from app.models import User

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

class TestAuth:
    def test_register_success(self, client):
        response = client.post('/auth/register',
                             data=json.dumps({
                                 'username': 'testuser',
                                 'password': 'testpass123'
                             }),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'ok'

    def test_register_duplicate_user(self, client, app):
        # Create user first
        with app.app_context():
            user = User(username='testuser', password_hash='dummy')
            db.session.add(user)
            db.session.commit()
        
        response = client.post('/auth/register',
                             data=json.dumps({
                                 'username': 'testuser',
                                 'password': 'testpass123'
                             }),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'user_exists'

    def test_login_success(self, client, app):
        from passlib.hash import bcrypt  # Use bcrypt instead of argon2
        
        # Create user first
        with app.app_context():
            user = User(username='testuser', 
                       password_hash=bcrypt.hash('testpass123'))
            db.session.add(user)
            db.session.commit()
        
        response = client.post('/auth/login',
                             data=json.dumps({
                                 'username': 'testuser',
                                 'password': 'testpass123'
                             }),
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'

    def test_login_invalid_credentials(self, client):
        response = client.post('/auth/login',
                             data=json.dumps({
                                 'username': 'nonexistent',
                                 'password': 'wrongpass'
                             }),
                             content_type='application/json')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['error'] == 'invalid_credentials'

    def test_login_invalid_payload(self, client):
        response = client.post('/auth/login',
                             data=json.dumps({
                                 'username': 'testuser'
                                 # missing password
                             }),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] == 'invalid_payload'
