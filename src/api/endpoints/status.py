from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.database import get_db
from src.models import ApiStatus
from src.schemas import Status

# Initialize the router
router = APIRouter(
    prefix="/status",
    tags=["Status"],
)


@router.get("/", response_model=Status, summary="Get the last database refresh time.")
def read_status(db: Session = Depends(get_db)):
    """
    Retrieves the global status record, indicating the last time the data was successfully updated
    by the refresh script.
    """
    # Based on the user's ApiStatus model (single-row table structure)
    status_row = db.query(ApiStatus).order_by(ApiStatus.id).first()

    if status_row is None:
        # This occurs if the database is new and the refresh script has never successfully run
        raise HTTPException(
            status_code=503,
            detail="API status not yet initialized. Data may be stale or empty. Run the refresh script.",
        )

    return status_row
