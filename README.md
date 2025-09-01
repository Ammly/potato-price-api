# Potato Price API

A production-ready API for estimating potato prices in Kenya, integrating weather data, market dynamics, and economic factors.

## Features

- **JWT Authentication**: Secure API access with Argon2 password hashing
- **Price Estimation**: Multi-factor algorithmic pricing with weather integration
- **Weather Integration**: OpenWeatherMap API integration for real-time weather data
- **Market Data**: Support for multiple markets with distance-weighted pricing
- **Celery Tasks**: Background processing for weather data fetching
- **Redis Caching**: High-performance caching and task queue
- **Database**: PostgreSQL with SQLAlchemy ORM and Alembic migrations

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Flask API     │    │   Celery        │    │   PostgreSQL    │
│   (Gunicorn)    │◄──►│   Workers       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Redis Cache   │    │   OpenWeather   │    │   Docker        │
│   & Queue       │    │   API           │    │   Compose       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenWeatherMap API key ([Get here](https://openweathermap.org/api))

### Setup

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd potato-price-api
   cp .env.example .env
   ```

2. **Update environment variables**:
   ```bash
   # Edit .env file with your values
   JWT_SECRET=your-super-secret-jwt-key
   SECRET_KEY=your-flask-secret-key
   WEATHER_API_KEY=your-openweathermap-api-key
   ```

3. **Start the services**:
   ```bash
   docker compose up --build
   ```

4. **Initialize database**:
   ```bash
   # Run migrations
   docker compose run --rm web flask db upgrade
   
   # Seed with sample data
   docker compose run --rm web python seed_data.py
   ```

## 📚 API Documentation

- **[🚀 Frontend Quick Start Guide](./docs/FRONTEND_QUICKSTART.md)** - **START HERE** for frontend developers
- **[Complete API Documentation](./docs/API_DOCUMENTATION.md)** - Comprehensive endpoint reference
- **[Interactive Testing](./api.http)** - VS Code REST Client requests for all endpoints
- **[PRD Specification](./docs/prd.md)** - Product requirements and technical specifications

### Quick API Reference

| Endpoint           | Method | Description           | Auth |
| ------------------ | ------ | --------------------- | ---- |
| `/health`          | GET    | System health check   | No   |
| `/auth/register`   | POST   | Create user account   | No   |
| `/auth/login`      | POST   | Get JWT token         | No   |
| `/prices/markets`  | GET    | List markets & prices | No   |
| `/prices/estimate` | POST   | Get price estimate    | Yes  |
| `/weather/latest`  | GET    | Latest weather data   | No   |
| `/weather/history` | GET    | Historical weather    | No   |

**Default credentials**: `admin` / `admin123`
   ```

3. **Start services**:
   ```bash
   docker compose up --build
   ```

4. **Run database migrations** (in another terminal):
   ```bash
   docker compose exec web flask db upgrade
   ```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication

#### Register User
```bash
POST /auth/register
Content-Type: application/json

{
  "username": "user123",
  "password": "securepassword"
}
```

#### Login
```bash
POST /auth/login
Content-Type: application/json

{
  "username": "user123",
  "password": "securepassword"
}

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1Q...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Price Estimation

#### Get Price Estimate
```bash
POST /prices/estimate
Authorization: Bearer <token>
Content-Type: application/json

{
  "location": "Nairobi",
  "logistics_mode": "wholesale",
  "variety_grade_factor": 1.0,
  "season_index": 0.2,
  "shock_index": 0.0,
  "weather_override": 0.3,
  "overrides": {
    "Nairobi": 120.0,
    "Nakuru": 110.0
  }
}

# Response:
{
  "estimate": 118.45,
  "units": "KES/kg",
  "range": [115.23, 121.67],
  "explain": {
    "base_smoothed": 115.2,
    "season_mult": 1.024,
    "logistics_mult": 1.0,
    "shock_mult": 1.0,
    "weather_mult": 1.036,
    "variety_mult": 1.0
  },
  "sources": ["KAMIS/NPCK (db)"]
}
```

**Parameters:**
- `location`: Target market location
- `logistics_mode`: `farmgate` | `wholesale` | `retail`
- `variety_grade_factor`: 0.5-2.0 (quality multiplier)
- `season_index`: -1.0 to 1.0 (seasonal adjustment)
- `shock_index`: -1.0 to 1.0 (market shock adjustment)
- `weather_override`: 0.0-1.0 (override weather impact)
- `overrides`: Market price overrides

### Weather Data

#### Get Latest Weather
```bash
GET /weather/latest?location=Nairobi

# Response:
{
  "timestamp": "2025-09-01T12:00:00",
  "rain_mm": 5.2,
  "weather_index": 0.17,
  "weather_code": "500",
  "raw": { ... }
}
```

## Development

### Running Tests

```bash
# Run all tests
docker compose exec web pytest

# Run specific test file
docker compose exec web pytest tests/test_estimator.py

# Run with coverage
docker compose exec web pytest --cov=app tests/
```

### Manual Testing

```bash
# Health check
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'

# Login (Fish shell)
set TOKEN (curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}' | jq -r '.access_token')

# Get estimate
curl -X POST http://localhost:8000/prices/estimate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"location": "Nairobi", "logistics_mode": "wholesale", "variety_grade_factor": 1.0}'
```

### Database Migrations

```bash
# Create migration
docker compose exec web flask db migrate -m "Add new table"

# Apply migrations
docker compose exec web flask db upgrade

# Downgrade
docker compose exec web flask db downgrade
```

### Celery Monitoring

```bash
# View worker status
docker compose exec worker celery -A app.celery_app inspect active

# View scheduled tasks
docker compose exec beat celery -A app.celery_app inspect scheduled
```

## Configuration

### Environment Variables

| Variable          | Description                  | Default                                             |
| ----------------- | ---------------------------- | --------------------------------------------------- |
| `DATABASE_URL`    | PostgreSQL connection string | `postgresql://postgres:postgres@db:5432/potato_api` |
| `REDIS_URL`       | Redis connection string      | `redis://redis:6379/0`                              |
| `JWT_SECRET`      | JWT signing secret           | **Required**                                        |
| `JWT_EXP_SECONDS` | JWT token expiry             | `900` (15 minutes)                                  |
| `SECRET_KEY`      | Flask secret key             | **Required**                                        |
| `WEATHER_API_KEY` | OpenWeatherMap API key       | **Required**                                        |
| `FLASK_ENV`       | Environment mode             | `development`                                       |

### Production Deployment

1. **Set production environment**:
   ```bash
   FLASK_ENV=production
   ```

2. **Use strong secrets**:
   ```bash
   JWT_SECRET=$(openssl rand -hex 32)
   SECRET_KEY=$(openssl rand -hex 32)
   ```

3. **Configure SSL/TLS** (use nginx or load balancer)

4. **Scale workers**:
   ```bash
   docker compose up --scale worker=3 --scale beat=1
   ```

## Estimator Algorithm

The price estimation uses a **rule-based multi-factor model**:

```
P_hat = Base × Season × Logistics × Shock × Weather × Variety

Where:
- Base: Distance-weighted average of market prices with EWMA smoothing
- Season: Seasonal adjustment factor (fixed coefficient × season_index)
- Logistics: Mode multiplier (farmgate: 0.9, wholesale: 1.0, retail: 1.2)
- Shock: Market shock adjustment (fixed coefficient × shock_index)
- Weather: Weather impact factor (fixed coefficient × weather_index)
- Variety: Quality/grade multiplier
```

**Note**: This is a deterministic algorithm with fixed coefficients. Future versions could incorporate machine learning models trained on historical price data for learned parameter optimization.

## API Response Codes

| Code | Description                          |
| ---- | ------------------------------------ |
| 200  | Success                              |
| 201  | Created                              |
| 400  | Bad Request (validation error)       |
| 401  | Unauthorized (invalid/missing token) |
| 404  | Not Found                            |
| 500  | Internal Server Error                |

## License

MIT License - see LICENSE file for details.