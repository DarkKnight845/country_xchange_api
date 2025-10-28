from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# --- Helper Schema for consistent String datetime handling ---
class TimeStampMixin(BaseModel):
    # Matches the Column(String) type used in the SQLAlchemy models
    last_refreshed_at: str | datetime = Field(..., example="2025-10-27T10:00:00.000000")


class CountryBase(BaseModel):
    name: str = Field(..., example="Nigeria")
    population: int = Field(..., example=206139589)
    currency_code: Optional[str] = Field(None, example="NGN")


class CountryResponse(CountryBase, TimeStampMixin):
    # Renamed from CountryCreated to CountryResponse for clarity in the API context
    id: int
    capital: Optional[str] = Field(None, example="Abuja")
    region: Optional[str] = Field(None, example="Africa")
    exchange_rate: Optional[float] = Field(None, example=1600.23)
    estimated_gdp: Optional[float] = Field(None, example=25767448125.2)
    flag_url: Optional[str] = None

    class Config:
        from_attributes = True


class Status(BaseModel):
    # Schema for the ApiStatus model (id and last_updated)
    id: int
    last_updated: str = Field(..., example="2025-10-27T10:00:00.000000")

    class Config:
        from_attributes = True
