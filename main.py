from fastapi import FastAPI

# Import the routers from the src/api directory
from src.api.endpoints import country, status

# Import Base and engine needed for startup
# These objects are defined in src/database.py
from src.database import Base, engine

# Initialize FastAPI app
app = FastAPI(
    title="Global Data API",
    description="Modular FastAPI application providing refreshed country and global status data.",
    version="1.0.0",
)


# Dependency to ensure tables are created on startup
@app.on_event("startup")
def startup_event():
    """
    Called when the application starts up.
    Creates all tables defined in src/models.py if they don't already exist.
    """
    print("Ensuring database tables exist...")
    # Base.metadata.create_all(bind=engine) ensures the DB is ready for use
    Base.metadata.create_all(bind=engine)
    print("Database tables are ready.")


# Include the routers
# The endpoints from src/api/country.py will be available under /countries
app.include_router(country.router)
# The endpoints from src/api/status.py will be available under /status
app.include_router(status.router)

# To run the application, you would typically use Uvicorn from the terminal:
# uvicorn main:app --reload
