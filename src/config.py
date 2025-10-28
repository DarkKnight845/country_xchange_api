import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    secret_key = os.getenv("SECRET_KEY", "default_secret_key")
    database_url = os.getenv("DATABASE_URL", "sqlite:///default.db")
    countries_api_url = os.getenv(
        "COUNTRIES_API_URL",
        "https://restcountries.com/v2/all?fields=name,capital,region,population,flag,currencies",
    )
    exchange_rate_api_url = os.getenv(
        "EXCHANGE_RATE_API_URL", "https://open.er-api.com/v6/latest/USD"
    )
    cache_dir = os.getenv("CACHE_DIR", "cache")
