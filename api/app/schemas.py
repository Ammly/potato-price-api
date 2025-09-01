from pydantic import BaseModel, Field, ValidationError, condecimal
from typing import Dict, Optional
from datetime import datetime

class AuthRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiry in seconds
    refresh_expires_in: int  # Refresh token expiry in seconds

class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str  # New refresh token (rotation)
    token_type: str = "bearer"
    expires_in: int  # Access token expiry in seconds
    refresh_expires_in: int  # New refresh token expiry in seconds

class EstimateRequest(BaseModel):
    location: str
    logistics_mode: str = Field(..., pattern=r"^(farmgate|wholesale|retail)$")
    variety_grade_factor: float = Field(1.0, ge=0.5, le=2.0)
    season_index: Optional[float] = Field(0.0, ge=-1.0, le=1.0)
    shock_index: Optional[float] = Field(0.0, ge=-1.0, le=1.0)
    timestamp: Optional[datetime] = None
    overrides: Optional[Dict[str, float]] = None
    weather_override: Optional[float] = Field(None, ge=0.0, le=1.0)

class EstimateResponse(BaseModel):
    estimate: float
    units: str = "KES/kg"
    range: list[float]
    explain: dict
    sources: list[str]
