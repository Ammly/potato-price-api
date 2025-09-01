#!/bin/bash
# api/setup_migrations.sh

set -e  # Exit on any error

echo "🔧 Setting up Alembic migrations..."

# Set Flask app
export FLASK_APP=app.main:create_app
export PYTHONPATH=/app

# Initialize Alembic if not already done
if [ ! -d "migrations" ]; then
    echo "Initializing Alembic..."
    flask db init
    echo "✅ Alembic initialized"
else
    echo "📁 Migrations directory already exists"
fi

# Create initial migration
echo "Creating initial migration..."
flask db migrate -m "Initial migration with users, markets, prices, weather, and model state tables"

# Apply migration
echo "Applying migration..."
flask db upgrade

echo "✅ Migration setup completed!"
echo ""
echo "🌱 To seed the database with sample data, run:"
echo "python seed_data.py"
echo ""
echo "🚀 To start the services:"
echo "docker compose up --build"
