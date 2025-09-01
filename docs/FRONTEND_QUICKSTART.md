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

---

## 📱 Flutter/Android Developer Guide

### 🚀 Quick Setup for Flutter

```bash
# 1. Create new Flutter project
flutter create potato_price_app
cd potato_price_app

# 2. Add dependencies
flutter pub add http
flutter pub add shared_preferences
flutter pub add flutter_secure_storage

# 3. For Android network permissions, add to android/app/src/main/AndroidManifest.xml:
# <uses-permission android:name="android.permission.INTERNET" />
```

### 📦 Essential Packages for Potato Price API

```yaml
# pubspec.yaml
dependencies:
  flutter:
    sdk: flutter
  http: ^1.2.1                    # HTTP requests
  shared_preferences: ^2.2.2      # Token storage (less secure)
  flutter_secure_storage: ^9.0.0  # Secure token storage (recommended)
  dart_jsonwebtoken: ^2.12.2      # JWT token handling (optional)
```

### 🔐 Secure Token Management Service

```dart
// lib/services/token_service.dart
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import 'dart:async';

class TokenService {
  static const _storage = FlutterSecureStorage();
  static const String _accessTokenKey = 'access_token';
  static const String _refreshTokenKey = 'refresh_token';
  static const String _tokenExpiryKey = 'token_expiry';
  
  Timer? _refreshTimer;
  
  // Save tokens securely
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
    required int expiresIn,
  }) async {
    final expiryTime = DateTime.now().add(Duration(seconds: expiresIn));
    
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
    await _storage.write(key: _tokenExpiryKey, value: expiryTime.toIso8601String());
    
    // Schedule auto-refresh 1 minute before expiry
    _scheduleTokenRefresh(expiresIn - 60);
  }
  
  // Get access token
  Future<String?> getAccessToken() async {
    final token = await _storage.read(key: _accessTokenKey);
    if (token == null) return null;
    
    // Check if token is expired
    if (await _isTokenExpired()) {
      await refreshToken();
      return await _storage.read(key: _accessTokenKey);
    }
    
    return token;
  }
  
  // Get refresh token
  Future<String?> getRefreshToken() async {
    return await _storage.read(key: _refreshTokenKey);
  }
  
  // Check if token is expired
  Future<bool> _isTokenExpired() async {
    final expiryString = await _storage.read(key: _tokenExpiryKey);
    if (expiryString == null) return true;
    
    final expiry = DateTime.parse(expiryString);
    return DateTime.now().isAfter(expiry);
  }
  
  // Clear all tokens
  Future<void> clearTokens() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
    await _storage.delete(key: _tokenExpiryKey);
    _refreshTimer?.cancel();
  }
  
  // Schedule automatic token refresh
  void _scheduleTokenRefresh(int delaySeconds) {
    _refreshTimer?.cancel();
    _refreshTimer = Timer(Duration(seconds: delaySeconds), () {
      refreshToken();
    });
  }
  
  // Refresh tokens using API
  Future<bool> refreshToken() async {
    final refreshTkn = await getRefreshToken();
    if (refreshTkn == null) return false;
    
    try {
      final response = await ApiService.refreshTokenRequest(refreshTkn);
      if (response != null) {
        await saveTokens(
          accessToken: response['access_token'],
          refreshToken: response['refresh_token'],
          expiresIn: response['expires_in'],
        );
        return true;
      }
    } catch (e) {
      print('Token refresh failed: $e');
      await clearTokens();
    }
    return false;
  }
}
```

### 🌐 API Service with Automatic Token Management

```dart
// lib/services/api_service.dart
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'token_service.dart';

class ApiService {
  static const String baseUrl = 'http://10.0.2.2:8000'; // Android emulator
  // static const String baseUrl = 'http://localhost:8000'; // iOS simulator
  // static const String baseUrl = 'https://your-api.com'; // Production
  
  static final TokenService _tokenService = TokenService();
  
  // Login and save tokens
  static Future<Map<String, dynamic>?> login(String username, String password) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'username': username,
          'password': password,
        }),
      );
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        await _tokenService.saveTokens(
          accessToken: data['access_token'],
          refreshToken: data['refresh_token'],
          expiresIn: data['expires_in'],
        );
        return data;
      }
    } catch (e) {
      print('Login error: $e');
    }
    return null;
  }
  
  // Logout and clear tokens
  static Future<void> logout() async {
    final refreshToken = await _tokenService.getRefreshToken();
    if (refreshToken != null) {
      try {
        await http.post(
          Uri.parse('$baseUrl/auth/revoke'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'refresh_token': refreshToken}),
        );
      } catch (e) {
        print('Logout error: $e');
      }
    }
    await _tokenService.clearTokens();
  }
  
  // Make authenticated API call
  static Future<Map<String, dynamic>?> authenticatedRequest(
    String endpoint, {
    String method = 'GET',
    Map<String, dynamic>? body,
  }) async {
    final token = await _tokenService.getAccessToken();
    if (token == null) throw Exception('No access token');
    
    http.Response response;
    final headers = {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer $token',
    };
    
    try {
      switch (method.toUpperCase()) {
        case 'POST':
          response = await http.post(
            Uri.parse('$baseUrl$endpoint'),
            headers: headers,
            body: body != null ? jsonEncode(body) : null,
          );
          break;
        case 'PUT':
          response = await http.put(
            Uri.parse('$baseUrl$endpoint'),
            headers: headers,
            body: body != null ? jsonEncode(body) : null,
          );
          break;
        case 'DELETE':
          response = await http.delete(
            Uri.parse('$baseUrl$endpoint'),
            headers: headers,
          );
          break;
        default:
          response = await http.get(
            Uri.parse('$baseUrl$endpoint'),
            headers: headers,
          );
      }
      
      if (response.statusCode == 401) {
        // Token expired, try refresh
        final refreshed = await _tokenService.refreshToken();
        if (refreshed) {
          // Retry request with new token
          final newToken = await _tokenService.getAccessToken();
          headers['Authorization'] = 'Bearer $newToken';
          
          switch (method.toUpperCase()) {
            case 'POST':
              response = await http.post(
                Uri.parse('$baseUrl$endpoint'),
                headers: headers,
                body: body != null ? jsonEncode(body) : null,
              );
              break;
            default:
              response = await http.get(
                Uri.parse('$baseUrl$endpoint'),
                headers: headers,
              );
          }
        } else {
          throw Exception('Authentication failed');
        }
      }
      
      if (response.statusCode >= 200 && response.statusCode < 300) {
        return jsonDecode(response.body);
      } else {
        throw Exception('API Error: ${response.statusCode} - ${response.body}');
      }
    } catch (e) {
      print('API request error: $e');
      rethrow;
    }
  }
  
  // Refresh token API call
  static Future<Map<String, dynamic>?> refreshTokenRequest(String refreshToken) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/auth/refresh'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'refresh_token': refreshToken}),
      );
      
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print('Refresh token error: $e');
    }
    return null;
  }
  
  // Get price estimate
  static Future<Map<String, dynamic>?> getPriceEstimate({
    required String location,
    required String logisticsMode,
    required double varietyGradeFactor,
    double? seasonIndex,
    double? shockIndex,
    double? weatherOverride,
    Map<String, double>? overrides,
  }) async {
    return await authenticatedRequest(
      '/prices/estimate',
      method: 'POST',
      body: {
        'location': location,
        'logistics_mode': logisticsMode,
        'variety_grade_factor': varietyGradeFactor,
        if (seasonIndex != null) 'season_index': seasonIndex,
        if (shockIndex != null) 'shock_index': shockIndex,
        if (weatherOverride != null) 'weather_override': weatherOverride,
        if (overrides != null) 'overrides': overrides,
      },
    );
  }
  
  // Get markets (no auth required)
  static Future<Map<String, dynamic>?> getMarkets() async {
    try {
      final response = await http.get(Uri.parse('$baseUrl/prices/markets'));
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print('Get markets error: $e');
    }
    return null;
  }
  
  // Get weather (no auth required)
  static Future<Map<String, dynamic>?> getWeather(String location) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/weather/latest?location=$location'),
      );
      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      }
    } catch (e) {
      print('Get weather error: $e');
    }
    return null;
  }
}
```

### 📱 Complete Flutter App Example

```dart
// lib/main.dart
import 'package:flutter/material.dart';
import 'services/api_service.dart';
import 'services/token_service.dart';

void main() {
  runApp(PotatoPriceApp());
}

class PotatoPriceApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Potato Price Estimator',
      theme: ThemeData(
        primarySwatch: Colors.orange,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: AuthChecker(),
    );
  }
}

class AuthChecker extends StatefulWidget {
  @override
  _AuthCheckerState createState() => _AuthCheckerState();
}

class _AuthCheckerState extends State<AuthChecker> {
  final TokenService _tokenService = TokenService();
  bool _isLoading = true;
  bool _isAuthenticated = false;

  @override
  void initState() {
    super.initState();
    _checkAuthStatus();
  }

  Future<void> _checkAuthStatus() async {
    final token = await _tokenService.getAccessToken();
    setState(() {
      _isAuthenticated = token != null;
      _isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return _isAuthenticated ? HomeScreen() : LoginScreen();
  }
}

class LoginScreen extends StatefulWidget {
  @override
  _LoginScreenState createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _usernameController = TextEditingController(text: 'admin');
  final _passwordController = TextEditingController(text: 'admin123');
  bool _isLoading = false;

  Future<void> _login() async {
    setState(() => _isLoading = true);
    
    try {
      final result = await ApiService.login(
        _usernameController.text,
        _passwordController.text,
      );
      
      if (result != null) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (context) => HomeScreen()),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Login failed'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Potato Price API')),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.agriculture, size: 80, color: Colors.orange),
            SizedBox(height: 32),
            TextField(
              controller: _usernameController,
              decoration: InputDecoration(
                labelText: 'Username',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            TextField(
              controller: _passwordController,
              decoration: InputDecoration(
                labelText: 'Password',
                border: OutlineInputBorder(),
              ),
              obscureText: true,
            ),
            SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _login,
                child: _isLoading 
                  ? CircularProgressIndicator(color: Colors.white)
                  : Text('Login'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _locationController = TextEditingController(text: 'Nyandarua');
  String _selectedMode = 'wholesale';
  double _varietyFactor = 1.0;
  double _seasonIndex = 0.0;
  Map<String, dynamic>? _estimate;
  List<dynamic>? _markets;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _loadMarkets();
  }

  Future<void> _loadMarkets() async {
    try {
      final markets = await ApiService.getMarkets();
      setState(() => _markets = markets?['markets']);
    } catch (e) {
      print('Failed to load markets: $e');
    }
  }

  Future<void> _getPriceEstimate() async {
    if (_locationController.text.isEmpty) return;
    
    setState(() => _isLoading = true);
    
    try {
      final estimate = await ApiService.getPriceEstimate(
        location: _locationController.text,
        logisticsMode: _selectedMode,
        varietyGradeFactor: _varietyFactor,
        seasonIndex: _seasonIndex,
      );
      
      setState(() => _estimate = estimate);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
      );
    } finally {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _logout() async {
    await ApiService.logout();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (context) => LoginScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Potato Price Estimator'),
        actions: [
          IconButton(
            icon: Icon(Icons.logout),
            onPressed: _logout,
          ),
        ],
      ),
      body: Padding(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Location input
            TextField(
              controller: _locationController,
              decoration: InputDecoration(
                labelText: 'Location',
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 16),
            
            // Logistics mode dropdown
            DropdownButtonFormField<String>(
              value: _selectedMode,
              decoration: InputDecoration(
                labelText: 'Logistics Mode',
                border: OutlineInputBorder(),
              ),
              items: ['farmgate', 'wholesale', 'retail']
                  .map((mode) => DropdownMenuItem(
                        value: mode,
                        child: Text(mode.toUpperCase()),
                      ))
                  .toList(),
              onChanged: (value) => setState(() => _selectedMode = value!),
            ),
            SizedBox(height: 16),
            
            // Variety factor slider
            Text('Variety Grade Factor: ${_varietyFactor.toStringAsFixed(1)}'),
            Slider(
              value: _varietyFactor,
              min: 0.5,
              max: 2.0,
              divisions: 15,
              onChanged: (value) => setState(() => _varietyFactor = value),
            ),
            SizedBox(height: 16),
            
            // Season index slider
            Text('Season Index: ${_seasonIndex.toStringAsFixed(1)}'),
            Slider(
              value: _seasonIndex,
              min: -1.0,
              max: 1.0,
              divisions: 20,
              onChanged: (value) => setState(() => _seasonIndex = value),
            ),
            SizedBox(height: 24),
            
            // Get estimate button
            ElevatedButton(
              onPressed: _isLoading ? null : _getPriceEstimate,
              child: _isLoading 
                ? CircularProgressIndicator(color: Colors.white)
                : Text('Get Price Estimate'),
            ),
            SizedBox(height: 24),
            
            // Results
            if (_estimate != null) ...[
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Price Estimate',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 8),
                      Text(
                        '${_estimate!['estimate'].toStringAsFixed(2)} ${_estimate!['units']}',
                        style: TextStyle(fontSize: 24, color: Colors.green),
                      ),
                      Text(
                        'Range: ${_estimate!['range'][0].toStringAsFixed(2)} - ${_estimate!['range'][1].toStringAsFixed(2)}',
                        style: TextStyle(color: Colors.grey[600]),
                      ),
                      SizedBox(height: 8),
                      Text('Breakdown:', style: TextStyle(fontWeight: FontWeight.bold)),
                      ...(_estimate!['explain'] as Map).entries.map(
                        (entry) => Text('${entry.key}: ${entry.value.toStringAsFixed(3)}'),
                      ),
                    ],
                  ),
                ),
              ),
            ],
            
            // Markets info
            if (_markets != null) ...[
              SizedBox(height: 16),
              Text('Available Markets:', style: TextStyle(fontWeight: FontWeight.bold)),
              Expanded(
                child: ListView.builder(
                  itemCount: _markets!.length,
                  itemBuilder: (context, index) {
                    final market = _markets![index];
                    return ListTile(
                      title: Text(market['name']),
                      subtitle: Text('${market['county']} - Latest: ${market['latest_price']['price_kg']} KES/kg'),
                      onTap: () {
                        _locationController.text = market['name'];
                      },
                    );
                  },
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
```

### 🔒 Android Security Considerations

```xml
<!-- android/app/src/main/AndroidManifest.xml -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <!-- Network permissions -->
    <uses-permission android:name="android.permission.INTERNET" />
    
    <!-- For development only - remove in production -->
    <application
        android:usesCleartextTraffic="true">
        
        <!-- Your existing application configuration -->
    </application>
</manifest>
```

### 🚀 Production Deployment Checklist

```dart
// lib/config/app_config.dart
class AppConfig {
  static const bool isProduction = bool.fromEnvironment('PRODUCTION');
  
  static String get apiBaseUrl {
    if (isProduction) {
      return 'https://your-potato-api.com';
    } else {
      // Development URLs
      return 'http://10.0.2.2:8000'; // Android emulator
      // return 'http://localhost:8000'; // iOS simulator
    }
  }
  
  static const Duration tokenRefreshBuffer = Duration(minutes: 1);
  static const Duration requestTimeout = Duration(seconds: 30);
}
```

### 🧪 Testing Your Flutter Integration

```bash
# Test on Android emulator
flutter run

# Test API connectivity
adb shell
# curl http://10.0.2.2:8000/health

# Test on physical device (replace IP with your computer's IP)
# flutter run --dart-define=API_BASE_URL=http://192.168.1.100:8000
```

### 📊 Flutter Data Models

```dart
// lib/models/potato_models.dart
class LoginResponse {
  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
  final int refreshExpiresIn;

  LoginResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
    required this.refreshExpiresIn,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) {
    return LoginResponse(
      accessToken: json['access_token'],
      refreshToken: json['refresh_token'],
      tokenType: json['token_type'],
      expiresIn: json['expires_in'],
      refreshExpiresIn: json['refresh_expires_in'],
    );
  }
}

class PriceEstimate {
  final double estimate;
  final String units;
  final List<double> range;
  final Map<String, double> explain;
  final List<String> sources;

  PriceEstimate({
    required this.estimate,
    required this.units,
    required this.range,
    required this.explain,
    required this.sources,
  });

  factory PriceEstimate.fromJson(Map<String, dynamic> json) {
    return PriceEstimate(
      estimate: json['estimate'].toDouble(),
      units: json['units'],
      range: List<double>.from(json['range'].map((x) => x.toDouble())),
      explain: Map<String, double>.from(
        json['explain'].map((key, value) => MapEntry(key, value.toDouble())),
      ),
      sources: List<String>.from(json['sources']),
    );
  }
}

class Market {
  final int id;
  final String name;
  final String county;
  final double lat;
  final double lon;
  final LatestPrice latestPrice;

  Market({
    required this.id,
    required this.name,
    required this.county,
    required this.lat,
    required this.lon,
    required this.latestPrice,
  });

  factory Market.fromJson(Map<String, dynamic> json) {
    return Market(
      id: json['id'],
      name: json['name'],
      county: json['county'],
      lat: json['lat'].toDouble(),
      lon: json['lon'].toDouble(),
      latestPrice: LatestPrice.fromJson(json['latest_price']),
    );
  }
}

class LatestPrice {
  final double priceKg;
  final String date;
  final String source;

  LatestPrice({
    required this.priceKg,
    required this.date,
    required this.source,
  });

  factory LatestPrice.fromJson(Map<String, dynamic> json) {
    return LatestPrice(
      priceKg: json['price_kg'].toDouble(),
      date: json['date'],
      source: json['source'],
    );
  }
}
```

### 🎯 Key Flutter/Android Tips

1. **Network Configuration**:
   - Use `10.0.2.2:8000` for Android emulator
   - Use device IP for physical Android devices
   - Add INTERNET permission in AndroidManifest.xml

2. **Secure Storage**:
   - Use `flutter_secure_storage` for tokens (encrypts data)
   - Fallback to `shared_preferences` for non-sensitive data
   - Always handle storage exceptions

3. **Token Management**:
   - Implement automatic token refresh
   - Store expiry times and schedule refresh
   - Handle authentication failures gracefully

4. **API Integration**:
   - Use proper error handling with try-catch
   - Implement retry logic for network failures
   - Show loading states for better UX

5. **Production Readiness**:
   - Remove `usesCleartextTraffic` for production
   - Use environment variables for API URLs
   - Implement proper certificate pinning for HTTPS
