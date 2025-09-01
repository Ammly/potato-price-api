# PRD — Context-Aware Potato Price API (Nyandarua use case)

## Project summary

Build a production-ready REST API that estimates local potato prices (KES/kg) by combining market price feeds (KAMIS / NPCK), weather, and contextual signals (location, seasonality, logistics, product grade). The API will be implemented with **Flask + Pydantic**, persist data to **Postgres**, use **Redis** for caching and Celery broker/backend, run periodic ETL jobs (weather & residual computation) with **Celery + Beat**, and be containerized with **Docker Compose**. Security: JWT bearer tokens, Argon2 password hashing, TLS in production.

Primary goal: provide a transparent, explainable price estimate plus uncertainty band and provenance so researchers and end-users can see how “context” affected the result.

---

# Goals & success criteria

## Goals

* Provide accurate, context-aware price estimates for target localities (initial focus: Nyandarua).
* Make the model explainable: include contribution of each context factor (season, logistics, weather, shock, variety).
* Keep the system secure, production-ready, observable, and maintainable.
* Support scheduled ingestion of market data and weather and compute model-state artifacts (EWMA, residual sigma) automatically.

## Success criteria (acceptance)

* `POST /auth/login` returns a valid short-lived JWT; protected endpoints validate token.
* `POST /prices/estimate` returns an estimate + uncertainty band + explainable breakdown + sources.
* ETL tasks run periodically and populate `weather_data` and `model_state` (EWMA base + sigma).
* Unit tests exist for estimator core and auth; CI runs tests and builds Docker image.
* Docker Compose run: web + worker + beat + db + redis boot and operate.
* End-to-end demo: given sample KAMIS/NPCK prices and a weather condition, estimator returns a believable, explainable price and uncertainty.

---

# Target users & personas

* **Researcher / Thesis owner** (primary): needs to demonstrate the “science” of context-aware modelling and produce reproducible results and code/pseudo-code for presentations.
* **Analyst / Agronomist / Trader**: wants localized price estimates to inform buying/selling decisions.
* **Developer / Integrator**: wants an API to embed into apps (web/mobile) or dashboards.

---

# Scope

## In scope (MVP + immediate extras)

* Flask API with Blueprints: `auth`, `prices`, `weather`, `health`.
* JWT authentication (HS256) and Argon2 hashed user registration/login.
* Estimator core as a pure, testable function (distance-weighted base → EWMA → multipliers including weather → uncertainty).
* Pydantic request/response validation and OpenAPI generation (schema driven).
* Postgres models: users, markets, market\_prices, weather\_data, model\_state.
* Redis caching for estimates and Celery broker/backend for ETL.
* Celery periodic tasks: fetch weather for markets; compute residual sigma per location.
* Docker Compose (web, worker, beat, db, redis).
* Basic logging, error handling, and test coverage for core functions.

## Out of scope (initial release)

* Multi-tenant billing, UI beyond examples, OAuth2 third-party flows, advanced ML models (though system should be extensible), production load balancing (k8s), managed secrets store (but recommended).

---

# Requirements

## Functional requirements

1. **Authentication**

   * `POST /auth/register` — create username/password (argon2).
   * `POST /auth/login` — returns `access_token` bearer JWT with `exp`.
2. **Estimate endpoint**

   * `POST /prices/estimate` (protected) — accepts context payload (location, logistics mode, season\_index, shock\_index, variety\_grade\_factor, overrides, weather\_override) and returns:

     * `estimate` (float, KES/kg)
     * `range` (lower, upper)
     * `explain` (component contributions)
     * `sources` (list)
3. **Weather**

   * `GET /weather/latest?location=Name` — returns latest cached weather data or fetches on demand (with rate-limit).
4. **Market/metadata**

   * `GET /prices/markets` — list markets + latest price (optional public or protected).
5. **ETL & model state**

   * Periodic task to fetch weather for registered markets and write WeatherData rows.
   * Periodic task to compute residual sigma for each market and store as `sigma:{market}` in ModelState.
6. **Cache**

   * Estimate responses cached in Redis (TTL e.g., 5–10 minutes) keyed by request hash + user.
7. **Explainability**

   * Estimator should return numeric multipliers / partials and the base\_smoothed value.
8. **OpenAPI**

   * Generate and expose OpenAPI docs from Pydantic schemas.

## Non-functional requirements

* **Security:** JWT short expiry (configurable), Argon2 hashed passwords, TLS enforced in production.
* **Scalability:** Redis caching and Celery workers to offload ETL; app runs behind Gunicorn.
* **Reliability:** Periodic ETL with retry/backoff and basic error observability (logs; Sentry optional).
* **Maintainability:** Clear code structure, tests, Alembic migrations, CI.
* **Extensibility:** Provider-agnostic weather adapter; estimator pure function to be replaced with ML models later.
* **Performance:** Typical estimate request latency under 200ms (if cached) and under 1s uncached (depending on DB read and compute).

---

# API specification (high-level)

## Auth

### POST /auth/register

Request:

```json
{ "username": "zaweria", "password": "StrongPass123" }
```

Response: `201 Created` `{ "status": "ok" }` or `400` if exists.

### POST /auth/login

Request:

```json
{ "username": "zaweria", "password": "StrongPass123" }
```

Response: `200 OK`

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

Errors: 401 invalid credentials.

## Prices

### POST /prices/estimate (protected)

Request (Pydantic `EstimateRequest`):

```json
{
  "location": "Nyandarua",
  "logistics_mode": "wholesale",
  "variety_grade_factor": 1.0,
  "season_index": 0.2,
  "shock_index": 0.0,
  "overrides": {"Nakuru": 32, "Nairobi": 30},
  "weather_override": 0.3
}
```

Response (`EstimateResponse`, 200):

```json
{
  "estimate": 29.10,
  "units": "KES/kg",
  "range": [27.00, 31.20],
  "explain": {
    "base_smoothed": 29.30,
    "season_mult": 0.96,
    "logistics_mult": 1.00,
    "shock_mult": 1.02,
    "weather_mult": 1.05,
    "variety_mult": 1.0
  },
  "sources": ["KAMIS/NPCK (db)", "weather: OpenWeatherMap (cached)"]
}
```

Errors: 400 invalid payload, 401 missing/invalid token, 500 internal.

### GET /prices/markets

Response: list markets and latest price.

## Weather

### GET /weather/latest?location={name}

Response (200):

```json
{
  "timestamp": "2025-08-20T10:00:00Z",
  "rain_mm": 8.5,
  "weather_index": 0.28,
  "weather_code": "500",
  "raw": { ... }
}
```

Errors: 400 missing location, 404 unknown location, 500 fetch error.

## Health

### GET /health

Returns minimal liveness/readiness JSON; integrates DB & Redis checks.

---

# Data model (core tables)

Summarized SQLAlchemy models; each will be included in migrations (Alembic):

* `users` (id PK, username unique, password\_hash, role, created\_at)
* `markets` (id PK, name unique, lat, lon, county, friction\_map JSON)
* `market_prices` (id PK, market\_id FK, date, price\_kg, source, created\_at)
* `weather_data` (id PK, market\_id FK, timestamp, rain\_mm, weather\_code, weather\_index, raw JSON)
* `model_state` (key PK, value JSON) — stores `base:{location}` and `sigma:{location}` etc.

Notes:

* `friction_map` is a market → location distance or trade-friction mapping to support distance-weighted base.
* `model_state` used for lightweight persisted model artifacts (EWMA base per location, sigma).

---

# Estimator algorithm (functional spec)

Inputs:

* Nearby market prices `price_ticker[m]`
* Distances / friction `dist(target, m)`
* `prev_base` (stored EWMA base for the target location)
* `season_index` ∈ \[-1, 1]
* `shock_index` ∈ \[-1, 1]
* `variety_grade_factor` float
* `weather_index` ∈ \[0, 1] (computed from weather ETL or override)
* Tunable: k1 (season sensitivity), k2 (shock sensitivity), k3 (weather sensitivity), alpha (EWMA smoothing)

Steps:

1. `w[m] = 1 / (1 + dist(target,m))`
2. `p_base_raw = Σ_m w[m] * price[m] / Σ_m w[m]`
3. `p_base_smoothed = EWMA(p_base_raw, prev_base, alpha)`
4. Multipliers:

   * `adj_season = 1 + k1 * season_index`
   * `adj_logistics = {farmgate:0.90, wholesale:1.00, retail:1.20}[logistics_mode]`
   * `adj_shock = 1 + k2 * shock_index`
   * `adj_weather = 1 + k3 * weather_index`
5. `p_hat = p_base_smoothed * adj_season * adj_logistics * adj_shock * adj_weather * variety_grade_factor`
6. `sigma = model_state['sigma:{location}']` if exists else fallback `max(0.5, 0.03 * p_hat)`
7. Return `p_hat`, `[p_hat - sigma, p_hat + sigma]`, and explain dict.

Rationale: hybrid rule-statistical approach (simple, explainable) with capacity to substitute ML models later.

---

# ETL & periodic jobs

## Tasks

* `fetch_weather_for_all_markets`: run every 15 minutes (configurable). Fetch from weather provider (OpenWeatherMap by default), write `weather_data` and cache latest in Redis `weather:latest:{market}`.
* `compute_sigma_for_all_locations`: run every 6 hours. Compute residuals across recent local price history and store `sigma:{market}` in `model_state`.
* Optional future: `fetch_market_prices` (KAMIS / NPCK ETL): scheduled fetcher to pull market price data (daily or weekly).

## Implementation notes

* Celery + Beat to schedule tasks. Redis used as broker & backend.
* ETL must respect provider rate limits and use exponential backoff on failures.
* Store raw payload for auditability; compute and persist normalized `weather_index`.

---

# Security & operational considerations

## Secrets & config

* Keep `JWT_SECRET`, DB credentials, `WEATHER_API_KEY`, and other secrets out of repo (env vars or Vault).
* Rotate JWT\_SECRET periodically; design supports RS256 stepping in future.

## Authentication & authorization

* JWT (HS256) signed tokens returned from `/auth/login`.
* Use short expiry (e.g., 15 minutes). Optionally implement refresh tokens with server-side revocation.

## Transport & production

* Enforce TLS (HTTPS) at reverse proxy (NGINX / load balancer).
* Run behind Gunicorn with multiple workers; use NGINX or an ingress in production for TLS/HTTP management.

## Rate limiting & abuse prevention

* Use Flask-Limiter with Redis backend. Tight limits on `/auth` endpoints and on weather-on-demand fetches.

## Logging & monitoring

* Structured logs (JSON) for critical events.
* Add Sentry for exceptions.
* Prometheus metrics for request rates, ETL job run times, failure counts, queue depth.

---

# Testing strategy

## Unit tests

* Estimator logic across many permutations (weather, season, shock, variety).
* JWT util encode/decode invariants.
* Auth register/login flows (unit + integration with test DB).

## Integration tests

* `POST /prices/estimate` end-to-end using test DB with seeded market and price data.
* `GET /weather/latest` using a mock/fake weather provider (or recorded responses).

## CI

* GitHub Actions workflow:

  * Lint (ruff/black), type checks (optional), unit tests, build Docker image, run basic integration smoke tests.
  * Prevent merging on failing tests.

---

# Observability & metrics

* Expose `/metrics` (Prometheus) or integrate with an exporter: track request latency, request success/error ratio, worker task durations, ETL failures, cache hit rate.
* Logs should include request id, user id (when authenticated), and request payload hashes (not raw secrets).

---

# Deployment & infrastructure

* **Local dev**: Docker Compose with `web`, `worker`, `beat`, `db:postgres:17.x`, `redis:8.x`.
* **Staging/Production**:

  * Container images pushed to registry.
  * Orchestrate on Kubernetes or Docker Compose on a VM.
  * Use managed Postgres (RDS/Cloud SQL) and managed Redis (Elasticache) for production scale.
  * Use TLS at ingress and a load balancer.
  * Backups: regular Postgres backups and Redis persistence decisions.

---

# Roadmap & milestones (implementation plan)

1. **MVP (done/ongoing)**

   * Scaffold, Flask app, Pydantic models, estimator function, basic endpoints, JWT auth, Argon2.
2. **Migrations & ETL (current)**

   * Alembic, Celery + Beat, weather ETL task, sigma computation, Redis caching.
3. **Testing & CI**

   * Add unit/integration tests, GitHub Actions CI.
4. **Production hardening**

   * Monitoring, Sentry, secrets management, TLS, rate limits, docs.
5. **Improvements & extensions**

   * Market price scrapers (KAMIS / NPCK) + scheduler, replace rule-based estimator with probabilistic model (Bayesian or ML ensemble), add an admin UI, refresh tokens & token revocation.

---

# Risks & mitigations

* **Weather provider rate limits or outages** — Mitigate: caching, failover provider adapter, backoff & alerting.
* **Data availability for some markets** — Mitigate: allow `overrides` and surface uncertainty; seed markets manually.
* **Model drift / correctness** — Mitigate: compute residuals/sigma, maintain ablation test suite, collect ground truth when possible.
* **Security leaks (secrets)** — Mitigate: env secrets only, secrets manager for prod, rotate keys.
* **Scaling workers** — Mitigate: scale Celery workers, shard tasks, use durable broker if needed (RabbitMQ).

---

# Acceptance checklist (concrete)

* [ ] `docker compose up --build` boots web + db + redis + worker + beat services.
* [ ] Migrations apply (`flask db upgrade`) creating tables.
* [ ] Register & login flows work; JWT validated on protected endpoints.
* [ ] `POST /prices/estimate` returns an estimate + explain for Nyandarua given sample data.
* [ ] Periodic Celery tasks populate weather\_data and model\_state (`base:...`, `sigma:...`).
* [ ] Redis caching applied for estimate responses and weather latest.
* [ ] Unit & integration tests pass in CI.

---

# Deliverables

* Production-ready Flask API repo with:

  * Codebase, Pydantic schemas, estimator, ETL tasks.
  * Alembic migrations.
  * Dockerfile + Docker Compose.
  * Unit & integration tests and CI workflow.
  * README with run instructions and architecture notes.
  * PRD (this document).

---

# Open questions / assumptions (documented)

* We assume English locale and KES/kg units.
* Weather provider: **OpenWeatherMap** chosen by default; keys required from you.
* Market price ETL for KAMIS/NPCK is planned but initial phase may rely on manual or seeded data.
* JWT uses HS256 signing (we can migrate to RS256 if needed).
* `friction_map` and distances should be precomputed; a future enhancement could compute actual road distances using external services (OSRM, GraphHopper).

---

# Next steps (immediate)

1. Add any market rows and geolocation (Nairobi, Nakuru, Nyeri, Nyandarua/Ol Kalou) to DB seed.
2. Provide `WEATHER_API_KEY` (OpenWeatherMap) in `.env`.
3. Run Compose, run migrations, start Celery worker + beat, seed market prices, and test `/prices/estimate`.
4. After validation, I will:

   * Add market price ETL (KAMIS/NPCK) scrapers,
   * Add full tests and CI,
   * Harden production deployment instructions.

---