# 🥔 Potato Price API Documentation

## Overview

The Potato Price API provides context-aware potato price estimates for Kenyan markets, combining market data, weather conditions, and contextual factors to deliver transparent, explainable pricing.

## Base URL
```
http://localhost:8000
```

## Authentication

All price estimation endpoints require JWT authentication.

### Flow
1. Register (optional) or use default admin account
2. Login to get access token
3. Include token in `Authorization: Bearer {token}` header

### Default Account
- **Username**: `admin`
- **Password**: `admin123`

---

## 📍 Endpoints

### 🏥 Health Check

#### `GET /health`
System health and connectivity check.

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2025-09-01T17:39:00Z",
  "services": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

---

### 🔐 Authentication

#### `POST /auth/register`
Create new user account.

**Rate Limit:** 5 requests/minute

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `201 Created`
```json
{
  "status": "ok"
}
```

**Errors:**
- `400` - User already exists

---

#### `POST /auth/login`
Authenticate and receive JWT access token and refresh token.

**Rate Limit:** 10 requests/minute

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "refresh_expires_in": 2592000
}
```

**Errors:**
- `401` - Invalid credentials

---

#### `POST /auth/refresh`
Exchange a refresh token for new access and refresh tokens (token rotation).

**Rate Limit:** 20 requests/minute

**Request:**
```json
{
  "refresh_token": "string"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 900,
  "refresh_expires_in": 2592000
}
```

**Errors:**
- `401` - Invalid, expired, or revoked refresh token

---

#### `POST /auth/revoke`
Revoke a specific refresh token.

**Rate Limit:** 10 requests/minute

**Request:**
```json
{
  "refresh_token": "string"
}
```

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Token revoked"
}
```

---

#### `POST /auth/revoke-all`
Revoke all refresh tokens for the authenticated user (logout from all devices).

**Authentication required**  
**Rate Limit:** 5 requests/minute

**Request:** Empty body

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Revoked 3 tokens"
}
```

---

### 🏪 Markets

#### `GET /prices/markets`
List all available markets with latest price data.

**No authentication required**

**Response:** `200 OK`
```json
{
  "count": 5,
  "markets": [
    {
      "id": 1,
      "name": "Nairobi",
      "county": "Nairobi", 
      "lat": -1.2921,
      "lon": 36.8219,
      "latest_price": {
        "price_kg": 96.48,
        "date": "2025-08-31T17:39:03.234397",
        "source": "seed_data"
      }
    }
  ]
}
```

---

### 💰 Price Estimation

#### `POST /prices/estimate`
Get context-aware price estimate with explainable breakdown.

**Authentication required**  
**Rate Limit:** 120 requests/minute  
**Cache:** 5 minutes TTL

**Request:**
```json
{
  "location": "string",                    // Target location
  "logistics_mode": "string",              // "farmgate" | "wholesale" | "retail"
  "variety_grade_factor": 1.0,             // 0.5-2.0 (quality multiplier)
  "season_index": 0.0,                     // Optional: -1.0 to 1.0 (abundant to scarce)
  "shock_index": 0.0,                      // Optional: -1.0 to 1.0 (market shock)
  "weather_override": 0.3,                 // Optional: 0.0-1.0 (weather impact)
  "overrides": {                           // Optional: override market prices
    "Nakuru": 95.0,
    "Nairobi": 100.0
  }
}
```

**Response:** `200 OK`
```json
{
  "estimate": 101.06,
  "units": "KES/kg",
  "range": [100.06, 102.06],
  "explain": {
    "base_smoothed": 98.693,
    "season_mult": 1.024,
    "logistics_mult": 1.0,
    "shock_mult": 1.0,
    "weather_mult": 1.0,
    "variety_mult": 1.0
  },
  "sources": ["KAMIS/NPCK (db)"]
}
```

**Parameter Details:**

| Parameter              | Type   | Range                     | Description                             |
| ---------------------- | ------ | ------------------------- | --------------------------------------- |
| `location`             | string | -                         | Target location for estimate            |
| `logistics_mode`       | string | farmgate/wholesale/retail | Distribution channel (0.9x/1.0x/1.2x)   |
| `variety_grade_factor` | float  | 0.5-2.0                   | Quality multiplier                      |
| `season_index`         | float  | -1.0 to 1.0               | Seasonal abundance (-1) to scarcity (1) |
| `shock_index`          | float  | -1.0 to 1.0               | Market shock factor                     |
| `weather_override`     | float  | 0.0-1.0                   | Manual weather impact override          |

**Errors:**
- `400` - Invalid request parameters
- `401` - Missing or invalid token
- `500` - Internal server error

---

### 🌤️ Weather

#### `GET /weather/latest?location={name}`
Get latest weather data for a market location.

**Rate Limit:** 60 requests/minute  
**Cache:** 2 hours TTL

**Parameters:**
- `location` (required): Market name

**Response:** `200 OK`
```json
{
  "timestamp": "2025-08-20T10:00:00Z",
  "rain_mm": 8.5,
  "weather_index": 0.28,
  "weather_code": "500",
  "source": "cache|database|api"
}
```

**Errors:**
- `400` - Missing location parameter
- `404` - Unknown location
- `500` - Weather fetch error

---

#### `GET /weather/history?location={name}&days={count}`
Get historical weather data.

**Rate Limit:** 30 requests/minute

**Parameters:**
- `location` (required): Market name
- `days` (optional): Number of days (default: 7, max: 30)

**Response:** `200 OK`
```json
{
  "location": "Nairobi",
  "days_requested": 7,
  "records_found": 10,
  "history": [
    {
      "timestamp": "2025-08-31T12:00:00Z",
      "rain_mm": 5.2,
      "weather_index": 0.17,
      "weather_code": "200"
    }
  ]
}
```

---

## 🚨 Error Handling

### Error Response Format
```json
{
  "error": "error_code",
  "details": "Human readable description"
}
```

### Common Error Codes
- `invalid_payload` - Malformed request
- `invalid_credentials` - Authentication failed
- `user_exists` - Registration conflict
- `missing_location` - Required parameter missing
- `unknown_location` - Location not found
- `fetch_error` - External API error
- `internal_error` - Server error

---

## 🎯 Rate Limits

| Endpoint                | Limit | Window   |
| ----------------------- | ----- | -------- |
| `POST /auth/register`   | 5     | 1 minute |
| `POST /auth/login`      | 10    | 1 minute |
| `POST /prices/estimate` | 120   | 1 minute |
| `GET /weather/latest`   | 60    | 1 minute |
| `GET /weather/history`  | 30    | 1 minute |

---

## 📊 Response Caching

| Endpoint        | Cache Duration |
| --------------- | -------------- |
| Price estimates | 5 minutes      |
| Weather data    | 2 hours        |
| Market data     | No cache       |

---

## 🔗 Integration Examples

### JavaScript/TypeScript
```typescript
interface EstimateRequest {
  location: string;
  logistics_mode: 'farmgate' | 'wholesale' | 'retail';
  variety_grade_factor: number;
  season_index?: number;
  shock_index?: number;
  weather_override?: number;
  overrides?: Record<string, number>;
}

async function getPriceEstimate(
  token: string, 
  request: EstimateRequest
): Promise<EstimateResponse> {
  const response = await fetch('http://localhost:8000/prices/estimate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify(request)
  });
  
  if (!response.ok) {
    throw new Error(`API Error: ${response.status}`);
  }
  
  return response.json();
}
```

### Python
```python
import requests

def get_price_estimate(token: str, location: str, logistics_mode: str) -> dict:
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    data = {
        'location': location,
        'logistics_mode': logistics_mode,
        'variety_grade_factor': 1.0
    }
    
    response = requests.post(
        'http://localhost:8000/prices/estimate',
        headers=headers,
        json=data
    )
    
    response.raise_for_status()
    return response.json()
```

### cURL
```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  | jq -r '.access_token')

# Get estimate
curl -X POST http://localhost:8000/prices/estimate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "location": "Nyandarua",
    "logistics_mode": "wholesale",
    "variety_grade_factor": 1.0,
    "season_index": 0.2
  }'
```

---

## 🧪 Testing

Use the provided `api.http` file with VS Code REST Client extension for interactive testing of all endpoints with various scenarios.

## 📈 Monitoring

- Health endpoint provides system status
- All requests include structured logging
- Rate limit headers included in responses

---

## 🔒 Security Notes

- JWT tokens expire in 15 minutes
- Passwords hashed with Argon2
- Rate limiting prevents abuse
- Input validation on all endpoints
- Use HTTPS in production
