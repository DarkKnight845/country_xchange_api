from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import Country
from src.schemas import CountryResponse

# Initialize the router
router = APIRouter(
    prefix="/countries",
    tags=["Countries"],
)


@router.get(
    "/",
    response_model=List[CountryResponse],
    summary="Retrieve a list of countries with filtering and sorting.",
)
def read_countries(
    db: Session = Depends(get_db),
    skip: int = Query(0, description="Number of items to skip (for pagination)"),
    limit: int = Query(100, description="Maximum number of items to return"),
    region: Optional[str] = Query(
        None, description="Filter by geographical region (e.g., Africa, Asia)"
    ),
    sort_by: Optional[str] = Query(
        "population",
        description="Sort by column: name, population, estimated_gdp. Defaults to descending for numbers.",
    ),
):
    """
    Fetches country data, allowing for pagination, filtering by region, and dynamic sorting.
    [Image of World Map Globe]
    """
    query = db.query(Country)

    # 1. Filter by Region (using ILIKE for case-insensitive partial match)
    if region:
        query = query.filter(Country.region.ilike(f"%{region}%"))

    # 2. Sorting Logic
    sort_column = None
    if sort_by == "name":
        sort_column = Country.name
    elif sort_by == "population":
        sort_column = Country.population
    elif sort_by == "estimated_gdp":
        sort_column = Country.estimated_gdp

    if sort_column is not None:
        # Sort descending for numbers, ascending for strings
        if sort_by in ["population", "estimated_gdp"]:
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

    # 3. Pagination
    countries = query.offset(skip).limit(limit).all()

    if not countries and skip > 0:
        raise HTTPException(
            status_code=404, detail="No more countries found in this range."
        )

    return countries


@router.get(
    "/{country_name}",
    response_model=CountryResponse,
    summary="Retrieve data for a specific country by name.",
)
def read_country_by_name(country_name: str, db: Session = Depends(get_db)):
    """
    Fetches a single country's details based on its exact name (case-sensitive).
    """
    # Use ILIKE for a slightly more forgiving search
    country = db.query(Country).filter(Country.name.ilike(country_name)).first()

    if country is None:
        raise HTTPException(
            status_code=404, detail=f"Country '{country_name}' not found"
        )

    return country
