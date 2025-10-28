import os
import random
import time
import traceback
from contextlib import contextmanager
from datetime import datetime

import requests

# --- 2. Database Setup (Self-Contained for Script Execution) ---
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

# --- 1. Project-Specific Imports (Adjusted for Standalone Script) ---
from src.config import Config
from src.models import ApiStatus, Base, Country  # Base is needed for table creation

# Get the database URL from the config
DATABASE_URL = Config.database_url

# Create the engine, which manages connections
engine = create_engine(DATABASE_URL)

# Create the session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session():
    """Context manager for providing a database session."""
    db_session = SessionLocal()
    try:
        yield db_session
        db_session.commit()  # Commit on successful exit
    except SQLAlchemyError as e:
        db_session.rollback()
        print(f"Database error occurred. Rolling back transaction: {e}")
        raise e
    except Exception as e:
        db_session.rollback()
        print(f"Unexpected error occurred. Rolling back transaction: {e}")
        raise e
    finally:
        db_session.close()


# --- 3. Core Logic Functions ---


def fetch_external_data():
    """Fetch exchange rates and country data from external APIs."""
    print("Fetching external data...")
    exchange_data = {}
    countries_data = []

    # Fetch exchange rates
    try:
        exchange_response = requests.get(Config.exchange_rate_api_url, timeout=10)
        exchange_response.raise_for_status()
        exchange_data = exchange_response.json().get("rates", {})
        print("Exchange rates fetched successfully.")
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch exchange rates: {e}")

    # Fetch countries data
    try:
        countries_response = requests.get(Config.countries_api_url, timeout=10)
        countries_response.raise_for_status()
        countries_data = countries_response.json()
        print(f"Countries data fetched successfully. ({len(countries_data)} records)")
    except requests.RequestException as e:
        print(f"ERROR: Failed to fetch countries data: {e}")

    return exchange_data, countries_data


def process_and_save_countries(
    db_session, exchange_data, countries_data, current_refresh_time
):
    """
    Process and save country data to the database.
    The current_refresh_time is passed to ensure consistency across all updated records.
    """
    updates_count = 0
    insert_count = 0

    print("Processing and saving country records...")

    for country_info in countries_data:
        country_name = country_info.get("name")
        population = country_info.get("population")

        currency_code = None
        if country_info.get("currencies") and country_info["currencies"]:
            currency_code = country_info["currencies"][0].get("code")

        # Default to 1.0 (USD) if rate is missing
        exchange_rate = exchange_data.get(currency_code, 1.0)

        estimated_gdp = None
        if exchange_rate and population is not None:
            # Using the simplified GDP calculation from the provided snippet
            estimated_gdp = population * exchange_rate * random.uniform(0.5, 1.5)

        # Build the Country object fields
        country_fields = {
            "name": country_name,
            "population": population,
            "currency_code": currency_code,
            "capital": country_info.get("capital"),
            "region": country_info.get("region"),
            "exchange_rate": exchange_rate,
            "estimated_gdp": estimated_gdp,
            "flag_url": country_info.get("flag"),
            # Ensure we pass the ISO string since the model column type is String
            "last_refreshed_at": current_refresh_time.isoformat(),
        }

        existing_country = (
            db_session.query(Country).filter(Country.name == country_name).first()
        )

        if existing_country:
            # Update existing record
            for key, value in country_fields.items():
                setattr(existing_country, key, value)
            updates_count += 1
        else:
            # Insert new record
            new_country = Country(**country_fields)
            db_session.add(new_country)
            insert_count += 1

    return updates_count, insert_count


def update_global_status(db_session, refresh_time):
    """
    Update the global API status (timestamp only) in the database,
    matching the user's ApiStatus model (id, last_updated).
    """
    print("Updating API status record...")

    # Try to find the single status row (often ID 1 for single-row tables)
    status_row = db_session.query(ApiStatus).order_by(ApiStatus.id).first()

    if not status_row:
        # If no row exists, create it
        status_row = ApiStatus(
            # No need to set ID, it's auto-incrementing
            last_updated=refresh_time.isoformat()
        )
        db_session.add(status_row)
    else:
        # If a row exists, update its timestamp
        status_row.last_updated = refresh_time.isoformat()


def refresh_main():
    """Main orchestration function for the refresh script."""
    start_time = time.time()

    # Get the expected database path from the URL
    db_path = DATABASE_URL.replace("sqlite:///", "")

    # 5. Ensure tables exist before running the logic
    print("Ensuring database tables exist...")
    try:
        # Check for the directory and create the database file if necessary
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        if os.path.exists(db_path):
            print(f"NOTE: Database file found at: {db_path}.")
            # Note about manual file deletion is CRITICAL for schema changes
            print(
                "If you still see 'IntegrityError: datatype mismatch' (referencing old columns),"
            )
            print(
                "it means your table schema is outdated. Please DELETE this file and rerun the script."
            )

        Base.metadata.create_all(bind=engine)
        print("Tables checked/created successfully.")
    except Exception as e:
        print(
            f"ERROR: Could not create database tables. Check DATABASE_URI and permissions. Error: {e}"
        )
        return

    # 4. Core Refresh Logic
    exchange_data, countries_data = fetch_external_data()

    if not countries_data:
        print("CRITICAL: Aborting refresh due to failure to load countries data.")
        return

    external_country_count = len(countries_data)
    current_refresh_time = datetime.utcnow()

    updates = 0
    inserts = 0
    total_countries = 0

    try:
        with get_db_session() as db_session:
            # Pass the consistent timestamp
            updates, inserts = process_and_save_countries(
                db_session, exchange_data, countries_data, current_refresh_time
            )

            # Update status records after country data has been processed (only passes timestamp)
            update_global_status(db_session, current_refresh_time)

            # Query the final count directly from the Country table
            total_countries = db_session.query(Country).count()

        end_time = time.time()
        print("\nSUCCESS: Data refresh complete.")
        print(f"-> Countries updated: {updates}")
        print(f"-> Countries inserted: {inserts}")
        print(f"-> Total Countries in database: {total_countries}")
        print(f"-> Last refresh time: {current_refresh_time.isoformat()}")
        print(f"Total time taken: {end_time - start_time:.2f} seconds.")

    except Exception as e:
        print(
            f"\nFATAL ERROR: The refresh process failed and changes were rolled back. Error: {e}"
        )
        traceback.print_exc()


if __name__ == "__main__":
    refresh_main()
