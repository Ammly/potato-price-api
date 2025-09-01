#!/usr/bin/env python3
# api/seed_data.py
"""
Script to seed the database with initial market and sample price data
"""
import os
import sys
from datetime import datetime, timedelta
import random

# Add the app to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app
from app.extensions import db
from app.models import Market, MarketPrice, User
from passlib.hash import argon2

def seed_markets():
    """Create initial market data"""
    markets_data = [
        {
            'name': 'Nairobi',
            'lat': -1.2921,
            'lon': 36.8219,
            'county': 'Nairobi',
            'friction_map': {'Nairobi': 0, 'Nakuru': 100, 'Nyeri': 80, 'Mombasa': 200}
        },
        {
            'name': 'Nakuru',
            'lat': -0.3031,
            'lon': 36.0800,
            'county': 'Nakuru',
            'friction_map': {'Nairobi': 100, 'Nakuru': 0, 'Nyeri': 60, 'Mombasa': 250}
        },
        {
            'name': 'Nyeri',
            'lat': -0.4167,
            'lon': 36.9500,
            'county': 'Nyeri',
            'friction_map': {'Nairobi': 80, 'Nakuru': 60, 'Nyeri': 0, 'Mombasa': 220}
        },
        {
            'name': 'Mombasa',
            'lat': -4.0435,
            'lon': 39.6682,
            'county': 'Mombasa',
            'friction_map': {'Nairobi': 200, 'Nakuru': 250, 'Nyeri': 220, 'Mombasa': 0}
        },
        {
            'name': 'Eldoret',
            'lat': 0.5143,
            'lon': 35.2697,
            'county': 'Uasin Gishu',
            'friction_map': {'Nairobi': 150, 'Nakuru': 80, 'Nyeri': 120, 'Mombasa': 300}
        }
    ]
    
    for market_data in markets_data:
        existing = Market.query.filter_by(name=market_data['name']).first()
        if not existing:
            market = Market(**market_data)
            db.session.add(market)
            print(f"Added market: {market_data['name']}")
    
    db.session.commit()

def seed_sample_prices():
    """Create sample price data for the last 30 days"""
    markets = Market.query.all()
    
    # Base prices for each market (KES per kg)
    base_prices = {
        'Nairobi': 95.0,
        'Nakuru': 88.0,
        'Nyeri': 92.0,
        'Mombasa': 105.0,
        'Eldoret': 85.0
    }
    
    # Generate prices for last 30 days
    for market in markets:
        base_price = base_prices.get(market.name, 90.0)
        
        for days_ago in range(30, 0, -1):
            date = datetime.utcnow() - timedelta(days=days_ago)
            
            # Add some random variation (±15%)
            variation = random.uniform(0.85, 1.15)
            price = round(base_price * variation, 2)
            
            existing = MarketPrice.query.filter_by(
                market_id=market.id,
                date=date.date()
            ).first()
            
            if not existing:
                market_price = MarketPrice(
                    market_id=market.id,
                    date=date,
                    price_kg=price,
                    source='seed_data'
                )
                db.session.add(market_price)
        
        print(f"Added sample prices for: {market.name}")
    
    db.session.commit()

def seed_admin_user():
    """Create an admin user"""
    username = 'admin'
    password = 'admin123'  # Change this in production!
    
    existing = User.query.filter_by(username=username).first()
    if not existing:
        user = User(
            username=username,
            password_hash=argon2.hash(password),
            role='admin'
        )
        db.session.add(user)
        db.session.commit()
        print(f"Created admin user: {username} / {password}")
        print("⚠️  Remember to change the admin password in production!")
    else:
        print("Admin user already exists")

def main():
    app = create_app()
    
    with app.app_context():
        print("🌱 Seeding database...")
        
        # Create tables if they don't exist
        db.create_all()
        
        # Seed data
        seed_markets()
        seed_sample_prices()
        seed_admin_user()
        
        print("✅ Database seeding completed!")
        
        # Print summary
        market_count = Market.query.count()
        price_count = MarketPrice.query.count()
        user_count = User.query.count()
        
        print(f"📊 Summary:")
        print(f"   Markets: {market_count}")
        print(f"   Price records: {price_count}")
        print(f"   Users: {user_count}")

if __name__ == '__main__':
    main()
