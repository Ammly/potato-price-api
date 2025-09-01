# 🚀 Frontend Developer Quick Start Guide

## TL;DR - Get Started in 5 Minutes

```bash
# 1. Start the API
docker compose up -d

# 2. Test it's working
curl http://localhost:8000/health

# 3. Get a token (Fish shell)
set TOKEN (curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.access_token')

# 4. Get a price estimate
curl -X POST http://localhost:8000/prices/estimate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"location": "Nyandarua", "logistics_mode": "wholesale", "variety_grade_factor": 1.0}'
```

**API Base URL**: `http://localhost:8000`
**Default Login**: `admin` / `admin123`

---

## 📋 Essential Endpoints for Frontend

### 🔑 Authentication (Required First)

```javascript
// 1. Login to get tokens
const loginResponse = await fetch('http://localhost:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'admin',
    password: 'admin123'
  })
});
const { access_token, refresh_token, expires_in, refresh_expires_in } = await loginResponse.json();
// Access token expires in 15 minutes (900 seconds)
// Refresh token expires in 30 days (2592000 seconds)

// 2. Store tokens securely (localStorage, sessionStorage, or secure HTTP-only cookies)
localStorage.setItem('access_token', access_token);
localStorage.setItem('refresh_token', refresh_token);

// 3. Refresh tokens when access token expires
const refreshResponse = await fetch('http://localhost:8000/auth/refresh', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    refresh_token: localStorage.getItem('refresh_token')
  })
});
const newTokens = await refreshResponse.json();
// Update stored tokens with new ones (token rotation)
localStorage.setItem('access_token', newTokens.access_token);
localStorage.setItem('refresh_token', newTokens.refresh_token);
```

### 💰 Price Estimation (Core Feature)

```javascript
// 2. Get price estimate (requires token)
const estimateResponse = await fetch('http://localhost:8000/prices/estimate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    location: 'Nyandarua',                    // Required: target location
    logistics_mode: 'wholesale',              // Required: farmgate|wholesale|retail
    variety_grade_factor: 1.0,                // Required: 0.5-2.0 (quality)
    season_index: 0.2,                        // Optional: -1.0 to 1.0 (seasonal)
    shock_index: 0.0,                         // Optional: -1.0 to 1.0 (disruption)
    weather_override: 0.3,                    // Optional: 0.0-1.0 (weather impact)
    overrides: { "Nairobi": 120.0 }           // Optional: override market prices
  })
});

const estimate = await estimateResponse.json();
// Returns: { estimate: 98.69, range: [97.69, 99.69], explain: {...}, units: "KES/kg" }
```

### 🏪 Markets Data (No Auth Required)

```javascript
// 3. Get available markets and current prices
const marketsResponse = await fetch('http://localhost:8000/prices/markets');
const { markets } = await marketsResponse.json();
// Returns: [{ id: 1, name: "Nairobi", latest_price: {...}, lat, lon, county }]
```

### 🌤️ Weather Data (No Auth Required)

```javascript
// 4. Get weather data for a market
const weatherResponse = await fetch('http://localhost:8000/weather/latest?location=Nairobi');
const weather = await weatherResponse.json();
// Returns: { rain_mm: 5.2, weather_index: 0.17, timestamp: "...", weather_code: "500" }
```

---

## 📊 Complete TypeScript Interface

```typescript
// Authentication
interface LoginRequest {
  username: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number; // Access token expiry in seconds (900 = 15 minutes)
  refresh_expires_in: number; // Refresh token expiry in seconds (2592000 = 30 days)
}

interface RefreshRequest {
  refresh_token: string;
}

interface RefreshResponse {
  access_token: string;
  refresh_token: string; // New refresh token (rotation)
  token_type: "bearer";
  expires_in: number; // Access token expiry in seconds
  refresh_expires_in: number; // New refresh token expiry in seconds
}

// Price Estimation
interface EstimateRequest {
  location: string;                              // Required
  logistics_mode: 'farmgate' | 'wholesale' | 'retail'; // Required
  variety_grade_factor: number;                  // Required: 0.5-2.0
  season_index?: number;                         // Optional: -1.0 to 1.0
  shock_index?: number;                          // Optional: -1.0 to 1.0
  weather_override?: number;                     // Optional: 0.0-1.0
  overrides?: Record<string, number>;            // Optional: market price overrides
}

interface EstimateResponse {
  estimate: number;                              // Final price estimate
  units: "KES/kg";                              // Always in Kenyan Shillings per kg
  range: [number, number];                       // Uncertainty range [min, max]
  explain: {                                     // Explainable breakdown
    base_smoothed: number;                       // Base price after smoothing
    season_mult: number;                         // Seasonal multiplier
    logistics_mult: number;                      // Logistics multiplier
    shock_mult: number;                          // Market shock multiplier
    weather_mult: number;                        // Weather multiplier
    variety_mult: number;                        // Variety/quality multiplier
  };
  sources: string[];                             // Data sources used
}

// Markets
interface Market {
  id: number;
  name: string;
  county: string;
  lat: number;
  lon: number;
  latest_price: {
    price_kg: number;
    date: string;
    source: string;
  };
}

interface MarketsResponse {
  count: number;
  markets: Market[];
}

// Weather
interface WeatherResponse {
  timestamp: string;
  rain_mm: number;
  weather_index: number;
  weather_code: string;
  source: "cache" | "database" | "api";
}

// Error Response
interface ApiError {
  error: string;
  details: string;
}
```

---

## 🎯 Rate Limits & Caching

| Endpoint                | Rate Limit | Cache Duration | Notes                    |
| ----------------------- | ---------- | -------------- | ------------------------ |
| `POST /auth/login`      | 10/minute  | None           | Tokens expire in 15min   |
| `POST /prices/estimate` | 120/minute | 5 minutes      | Cached by request params |
| `GET /weather/latest`   | 60/minute  | 2 hours        | Weather data cached      |
| `GET /prices/markets`   | No limit   | None           | Real-time market data    |

---

## ⚠️ Error Handling

```typescript
async function handleApiCall<T>(apiCall: () => Promise<Response>): Promise<T> {
  try {
    const response = await apiCall();
    
    if (!response.ok) {
      const error: ApiError = await response.json();
      
      switch (response.status) {
        case 400:
          throw new Error(`Validation Error: ${error.details}`);
        case 401:
          throw new Error('Authentication required or token expired');
        case 429:
          throw new Error('Rate limit exceeded - please wait');
        case 500:
          throw new Error('Server error - please try again');
        default:
          throw new Error(`API Error: ${error.details}`);
      }
    }
    
    return response.json();
  } catch (error) {
    console.error('API call failed:', error);
    throw error;
  }
}
```

---

## 🔧 Environment Setup

### Required for Development
1. **Docker & Docker Compose** - API runs in containers
2. **jq** (optional) - For testing with curl: `sudo apt install jq`

### API Configuration
- **Base URL**: `http://localhost:8000`
- **Default Port**: 8000
- **Health Check**: `GET /health`

### Weather API Note
⚠️ Weather endpoints return mock data until OpenWeatherMap API key is configured.
Price estimation works regardless - weather impact can be overridden manually.

---

## 🧪 Testing Your Integration

### Test Authentication Flow
```bash
# Fish shell syntax
set TOKEN (curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.access_token')

echo "Token: $TOKEN"
```

### Test Price Estimation
```bash
curl -X POST http://localhost:8000/prices/estimate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "location": "Nyandarua",
    "logistics_mode": "wholesale", 
    "variety_grade_factor": 1.0,
    "season_index": 0.2
  }' | jq
```

### Test Error Scenarios
```bash
# Invalid token
curl -X POST http://localhost:8000/prices/estimate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token" \
  -d '{"location": "Nyandarua", "logistics_mode": "wholesale", "variety_grade_factor": 1.0}'

# Invalid parameter
curl -X POST http://localhost:8000/prices/estimate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"location": "Nyandarua", "logistics_mode": "invalid", "variety_grade_factor": 1.0}'
```

---

## 📱 React/Next.js Example with Token Management

```tsx
import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

// Token management utility
class TokenManager {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshTimer: NodeJS.Timeout | null = null;

  constructor() {
    this.loadTokens();
  }

  loadTokens() {
    this.accessToken = localStorage.getItem('access_token');
    this.refreshToken = localStorage.getItem('refresh_token');
  }

  saveTokens(accessToken: string, refreshToken: string, expiresIn: number) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    
    // Schedule refresh 1 minute before expiry
    this.scheduleRefresh(expiresIn - 60);
  }

  async scheduleRefresh(delaySeconds: number) {
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
    
    this.refreshTimer = setTimeout(async () => {
      await this.refreshAccessToken();
    }, delaySeconds * 1000);
  }

  async refreshAccessToken(): Promise<boolean> {
    if (!this.refreshToken) return false;

    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken })
      });

      if (response.ok) {
        const tokens = await response.json();
        this.saveTokens(tokens.access_token, tokens.refresh_token, tokens.expires_in);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
    
    this.clearTokens();
    return false;
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    if (this.refreshTimer) clearTimeout(this.refreshTimer);
  }

  getAccessToken() {
    return this.accessToken;
  }

  async login(username: string, password: string): Promise<boolean> {
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (response.ok) {
        const tokens = await response.json();
        this.saveTokens(tokens.access_token, tokens.refresh_token, tokens.expires_in);
        return true;
      }
    } catch (error) {
      console.error('Login failed:', error);
    }
    return false;
  }

  async logout() {
    if (this.refreshToken) {
      try {
        await fetch(`${API_BASE}/auth/revoke`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken })
        });
      } catch (error) {
        console.error('Token revocation failed:', error);
      }
    }
    this.clearTokens();
  }
}

const tokenManager = new TokenManager();

export default function PotatoPriceApp() {
  const [estimate, setEstimate] = useState<EstimateResponse | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    setIsAuthenticated(!!tokenManager.getAccessToken());
  }, []);

  // API call with automatic token refresh
  async function apiCall<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const token = tokenManager.getAccessToken();
    if (!token) throw new Error('Not authenticated');

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
      }
    });

    // If token expired, try to refresh and retry
    if (response.status === 401) {
      const refreshed = await tokenManager.refreshAccessToken();
      if (refreshed) {
        const newToken = tokenManager.getAccessToken();
        const retryResponse = await fetch(`${API_BASE}${endpoint}`, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${newToken}`,
            ...options.headers
          }
        });
        return retryResponse.json();
      } else {
        setIsAuthenticated(false);
        throw new Error('Authentication failed');
      }
    }

    return response.json();
  }

  // Get price estimate with automatic token management
  async function getPriceEstimate() {
    try {
      const estimateData = await apiCall<EstimateResponse>('/prices/estimate', {
        method: 'POST',
        body: JSON.stringify({
          location: 'Nyandarua',
          logistics_mode: 'wholesale',
          variety_grade_factor: 1.0
        })
      });
      setEstimate(estimateData);
    } catch (error) {
      console.error('Failed to get estimate:', error);
    }
  }

  // Login function
  async function handleLogin() {
    const success = await tokenManager.login('admin', 'admin123');
    setIsAuthenticated(success);
  }

  // Logout function
  async function handleLogout() {
    await tokenManager.logout();
    setIsAuthenticated(false);
  }

  if (!isAuthenticated) {
    return (
      <div>
        <h1>Login Required</h1>
        <button onClick={handleLogin}>Login as Admin</button>
      </div>
    );
  }

  return (
    <div>
      <h1>Potato Price Estimator</h1>
      <button onClick={getPriceEstimate}>Get Price Estimate</button>
      <button onClick={handleLogout}>Logout</button>
      
      {estimate && (
        <div>
          <h2>Estimate: {estimate.estimate} {estimate.units}</h2>
          <p>Range: {estimate.range[0]} - {estimate.range[1]}</p>
          <p>Base Price: {estimate.explain.base_smoothed}</p>
        </div>
      )}
    </div>
  );
}
```

---

## 🔍 Debugging Tips

### Check API Status
```bash
# Health check
curl -s http://localhost:8000/health | jq

# Service status
docker compose ps

# View logs
docker compose logs web
docker compose logs worker
```

### Token Issues
- Tokens expire in 15 minutes (900 seconds)
- Check token format: should start with `eyJ`
- Verify `Authorization: Bearer {token}` header format

### Validation Errors
- `location`: Must be a string
- `logistics_mode`: Must be exactly "farmgate", "wholesale", or "retail"
- `variety_grade_factor`: Must be between 0.5 and 2.0
- `season_index`, `shock_index`: Must be between -1.0 and 1.0
- `weather_override`: Must be between 0.0 and 1.0

---

## 📚 Additional Resources

- **[Complete API Documentation](./API_DOCUMENTATION.md)** - Full endpoint reference
- **[Interactive Testing](./api.http)** - VS Code REST Client examples  
- **[Algorithm Details](./PRICING_ALGORITHM.md)** - How price estimation works
- **[PRD Specification](./prd.md)** - Technical requirements

---

## 🆘 Need Help?

1. **API not starting?** Check `docker compose ps` and logs
2. **Authentication failing?** Verify credentials: `admin` / `admin123`
3. **Estimation errors?** Check parameter validation rules above
4. **Rate limiting?** Wait 1 minute and retry, or use different endpoint

**The API is production-ready and thoroughly tested. Happy coding! 🥔**
