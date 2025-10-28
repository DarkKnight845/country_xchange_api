import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# Environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./countries.db")
# Handle Railway PostgreSQL URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Database setup
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Model
class CountryModel(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    capital = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True, index=True)
    population = Column(Integer, nullable=False)
    currency_code = Column(String(10), nullable=True, index=True)
    exchange_rate = Column(Float, nullable=True)
    estimated_gdp = Column(Float, nullable=True)
    flag_url = Column(String(500), nullable=True)
    last_refreshed_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# Create tables
Base.metadata.create_all(bind=engine)


# Pydantic Models
class CountryResponse(BaseModel):
    id: int
    name: str
    capital: Optional[str]
    region: Optional[str]
    population: int
    currency_code: Optional[str]
    exchange_rate: Optional[float]
    estimated_gdp: Optional[float]
    flag_url: Optional[str]
    last_refreshed_at: datetime

    class Config:
        from_attributes = True


class StatusResponse(BaseModel):
    total_countries: int
    last_refreshed_at: Optional[datetime]


class ErrorResponse(BaseModel):
    error: str
    details: Optional[dict] = None


# FastAPI app
app = FastAPI(title="Country Currency & Exchange API")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Helper functions
async def fetch_countries():
    """Fetch country data from REST Countries API"""
    url = "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies"
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "External data source unavailable",
                    "details": "Could not fetch data from REST Countries API: Request timeout",
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "External data source unavailable",
                    "details": f"Could not fetch data from REST Countries API: {str(e)}",
                },
            )


async def fetch_exchange_rates():
    """Fetch exchange rates from Exchange Rate API"""
    url = "https://open.er-api.com/v6/latest/USD"
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("rates", {})
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "External data source unavailable",
                    "details": "Could not fetch data from Exchange Rate API: Request timeout",
                },
            )
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "External data source unavailable",
                    "details": f"Could not fetch data from Exchange Rate API: {str(e)}",
                },
            )


def calculate_gdp(population: int, exchange_rate: Optional[float]) -> Optional[float]:
    """Calculate estimated GDP"""
    if exchange_rate is None or exchange_rate == 0:
        return None
    random_multiplier = random.uniform(1000, 2000)
    return (population * random_multiplier) / exchange_rate


def generate_summary_image(db: Session):
    """Generate summary image with country statistics"""
    # Create cache directory if it doesn't exist
    Path("cache").mkdir(exist_ok=True)

    # Get statistics
    total = db.query(CountryModel).count()
    top_countries = (
        db.query(CountryModel)
        .filter(CountryModel.estimated_gdp.isnot(None))
        .order_by(CountryModel.estimated_gdp.desc())
        .limit(5)
        .all()
    )

    last_refresh = db.query(func.max(CountryModel.last_refreshed_at)).scalar()

    # Create image
    width, height = 800, 600
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    # Try to use a better font, fallback to default
    try:
        title_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32
        )
        header_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
        )
        text_font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18
        )
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        text_font = ImageFont.load_default()

    # Draw content
    y_position = 50

    # Title
    draw.text((50, y_position), "Country Data Summary", fill="black", font=title_font)
    y_position += 60

    # Total countries
    draw.text(
        (50, y_position), f"Total Countries: {total}", fill="black", font=header_font
    )
    y_position += 50

    # Top 5 countries
    draw.text(
        (50, y_position),
        "Top 5 Countries by Estimated GDP:",
        fill="black",
        font=header_font,
    )
    y_position += 40

    for i, country in enumerate(top_countries, 1):
        gdp_formatted = (
            f"{country.estimated_gdp:,.2f}" if country.estimated_gdp else "N/A"
        )
        text = f"{i}. {country.name}: ${gdp_formatted}"
        draw.text((70, y_position), text, fill="black", font=text_font)
        y_position += 35

    # Last refresh
    y_position += 30
    refresh_time = (
        last_refresh.strftime("%Y-%m-%d %H:%M:%S UTC") if last_refresh else "Never"
    )
    draw.text(
        (50, y_position), f"Last Refreshed: {refresh_time}", fill="gray", font=text_font
    )

    # Save image
    img.save("cache/summary.png")


# API Endpoints
@app.post("/countries/refresh")
async def refresh_countries():
    """Fetch and cache all countries with exchange rates"""
    db = next(get_db())

    try:
        # Fetch data from external APIs
        print("Fetching countries data...")
        countries_data = await fetch_countries()
        print(f"Fetched {len(countries_data)} countries")

        print("Fetching exchange rates...")
        exchange_rates = await fetch_exchange_rates()
        print(f"Fetched {len(exchange_rates)} exchange rates")

        refresh_timestamp = datetime.utcnow()
        processed = 0

        for country_data in countries_data:
            try:
                name = country_data.get("name")
                if not name:
                    continue

                population = country_data.get("population", 0)
                if not population:
                    continue

                # Handle currency
                currencies = country_data.get("currencies", [])
                currency_code = None
                exchange_rate = None
                estimated_gdp = None

                if currencies and len(currencies) > 0:
                    currency_code = currencies[0].get("code")

                    if currency_code and currency_code in exchange_rates:
                        exchange_rate = exchange_rates[currency_code]
                        estimated_gdp = calculate_gdp(population, exchange_rate)

                # If no currency, set GDP to 0
                if not currency_code:
                    estimated_gdp = 0

                # Check if country exists
                existing_country = (
                    db.query(CountryModel)
                    .filter(func.lower(CountryModel.name) == name.lower())
                    .first()
                )

                if existing_country:
                    # Update existing
                    existing_country.capital = country_data.get("capital")
                    existing_country.region = country_data.get("region")
                    existing_country.population = population
                    existing_country.currency_code = currency_code
                    existing_country.exchange_rate = exchange_rate
                    existing_country.estimated_gdp = estimated_gdp
                    existing_country.flag_url = country_data.get("flag")
                    existing_country.last_refreshed_at = refresh_timestamp
                else:
                    # Insert new
                    new_country = CountryModel(
                        name=name,
                        capital=country_data.get("capital"),
                        region=country_data.get("region"),
                        population=population,
                        currency_code=currency_code,
                        exchange_rate=exchange_rate,
                        estimated_gdp=estimated_gdp,
                        flag_url=country_data.get("flag"),
                        last_refreshed_at=refresh_timestamp,
                    )
                    db.add(new_country)

                processed += 1

            except Exception as e:
                print(
                    f"Error processing country {country_data.get('name', 'unknown')}: {str(e)}"
                )
                continue

        db.commit()
        print(f"Committed {processed} countries to database")

        # Generate summary image
        try:
            generate_summary_image(db)
            print("Generated summary image")
        except Exception as e:
            print(f"Error generating image: {str(e)}")

        total = db.query(CountryModel).count()
        return {
            "message": "Countries refreshed successfully",
            "total_countries": total,
            "last_refreshed_at": refresh_timestamp.isoformat(),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Error in refresh: {str(e)}")
        import traceback

        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "details": str(e)},
        )
    finally:
        db.close()


@app.get("/countries/image")
async def get_summary_image():
    """Serve the generated summary image"""
    image_path = "cache/summary.png"

    if not os.path.exists(image_path):
        return JSONResponse(
            status_code=404, content={"error": "Summary image not found"}
        )

    return FileResponse(image_path, media_type="image/png")


@app.get("/countries")
async def get_countries(
    region: Optional[str] = Query(None),
    currency: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
):
    """Get all countries with optional filters and sorting"""
    db = next(get_db())

    try:
        query = db.query(CountryModel)

        # Apply filters
        if region:
            query = query.filter(func.lower(CountryModel.region) == region.lower())

        if currency:
            query = query.filter(
                func.lower(CountryModel.currency_code) == currency.lower()
            )

        # Apply sorting
        if sort == "gdp_desc":
            query = query.order_by(CountryModel.estimated_gdp.desc())
        elif sort == "gdp_asc":
            query = query.order_by(CountryModel.estimated_gdp.asc())
        elif sort == "name_asc":
            query = query.order_by(CountryModel.name.asc())
        elif sort == "name_desc":
            query = query.order_by(CountryModel.name.desc())

        countries = query.all()

        # Convert to dict format
        result = []
        for country in countries:
            result.append(
                {
                    "id": country.id,
                    "name": country.name,
                    "capital": country.capital,
                    "region": country.region,
                    "population": country.population,
                    "currency_code": country.currency_code,
                    "exchange_rate": country.exchange_rate,
                    "estimated_gdp": country.estimated_gdp,
                    "flag_url": country.flag_url,
                    "last_refreshed_at": country.last_refreshed_at.isoformat()
                    if country.last_refreshed_at
                    else None,
                }
            )

        return result

    finally:
        db.close()


@app.get("/countries/{name}")
async def get_country(name: str):
    """Get a single country by name"""
    db = next(get_db())

    try:
        country = (
            db.query(CountryModel)
            .filter(func.lower(CountryModel.name) == name.lower())
            .first()
        )

        if not country:
            return JSONResponse(status_code=404, content={"error": "Country not found"})

        return {
            "id": country.id,
            "name": country.name,
            "capital": country.capital,
            "region": country.region,
            "population": country.population,
            "currency_code": country.currency_code,
            "exchange_rate": country.exchange_rate,
            "estimated_gdp": country.estimated_gdp,
            "flag_url": country.flag_url,
            "last_refreshed_at": country.last_refreshed_at.isoformat()
            if country.last_refreshed_at
            else None,
        }

    finally:
        db.close()


@app.delete("/countries/{name}")
async def delete_country(name: str):
    """Delete a country by name"""
    db = next(get_db())

    try:
        country = (
            db.query(CountryModel)
            .filter(func.lower(CountryModel.name) == name.lower())
            .first()
        )

        if not country:
            return JSONResponse(status_code=404, content={"error": "Country not found"})

        db.delete(country)
        db.commit()

        return {"message": f"Country '{name}' deleted successfully"}

    finally:
        db.close()


@app.get("/status")
async def get_status():
    """Get system status"""
    db = next(get_db())

    try:
        total = db.query(CountryModel).count()
        last_refresh = db.query(func.max(CountryModel.last_refreshed_at)).scalar()

        return {
            "total_countries": total,
            "last_refreshed_at": last_refresh.isoformat() if last_refresh else None,
        }

    finally:
        db.close()


@app.get("/health")
async def health_check():
    """Health check endpoint to verify database connection"""
    db = next(get_db())

    try:
        # Try to query the database
        db.execute("SELECT 1")
        db_status = "connected"
        db_type = "PostgreSQL" if "postgresql" in DATABASE_URL else "SQLite"
    except Exception as e:
        db_status = "disconnected"
        db_type = "unknown"
        return {
            "status": "unhealthy",
            "database": {"status": db_status, "type": db_type, "error": str(e)},
        }
    finally:
        db.close()

    return {"status": "healthy", "database": {"status": db_status, "type": db_type}}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Country Currency & Exchange API",
        "endpoints": {
            "GET /health": "Health check and database status",
            "POST /countries/refresh": "Refresh country data",
            "GET /countries": "Get all countries (supports ?region=, ?currency=, ?sort=)",
            "GET /countries/{name}": "Get country by name",
            "DELETE /countries/{name}": "Delete country",
            "GET /status": "Get system status",
            "GET /countries/image": "Get summary image",
        },
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
