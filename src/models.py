from datetime import datetime

from sqlalchemy import Column, Float, Integer, String

from src.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    population = Column(Integer, nullable=False)
    currency_code = Column(String, nullable=True)
    capital = Column(String, nullable=True)
    region = Column(String, nullable=True)
    exchange_rate = Column(Float, nullable=True)
    estimated_gdp = Column(Float, nullable=True)
    flag_url = Column(String, nullable=True)
    last_refreshed_at = Column(
        String, default=datetime.utcnow().isoformat(), nullable=False
    )

    def to_dict(self):
        # Convert Numeric and DateTime to standard Python types for JSON serialization
        return {
            "id": self.id,
            "name": self.name,
            "capital": self.capital,
            "region": self.region,
            "population": self.population,
            "currency_code": self.currency_code,
            "exchange_rate": float(self.exchange_rate)
            if self.exchange_rate is not None
            else None,
            "estimated_gdp": float(self.estimated_gdp)
            if self.estimated_gdp is not None
            else None,
            "flag_url": self.flag_url,
            "last_refreshed_at": self.last_refreshed_at.isoformat() + "Z",
        }


class ApiStatus(Base):
    __tablename__ = "api_status"

    id = Column(Integer, primary_key=True, index=True)
    last_updated = Column(String, default=datetime.utcnow().isoformat(), nullable=False)
