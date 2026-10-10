
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.ml_model import predict_next_revenue
from backend.ai_assistant import generate_sales_insights

from backend.database import (
    initialize_database,
    get_all_sales,
    save_sale,
    import_sales_data,
)

app = FastAPI(
    title="Sales Analytics API",
    description="Backend API for Sales Analytics and AI Insights",
    version="1.0.0",
)

# Allow requests from the Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialize the database when the API starts."""
    initialize_database()


@app.get("/")
def home():
    """Check whether the API is running."""
    return {
        "status": "success",
        "message": "Sales Analytics API is running!",
    }


@app.get("/health")
def health_check():
    """Check API health."""
    return {"status": "healthy"}


@app.get("/api/sales")
def get_sales():
    """Return all sales records from SQLite."""
    return get_all_sales()


@app.get("/api/summary")
def sales_summary():
    """Return summary metrics from SQLite."""
    sales = get_all_sales()

    return {
        "total_revenue": sum(item["revenue"] for item in sales),
        "total_profit": sum(item["profit"] for item in sales),
        "total_orders": sum(item["orders"] for item in sales),
        "months_count": len(sales),
    }


class SaleInput(BaseModel):
    """Validate a single sales record."""

    month: str = Field(min_length=3, max_length=3)
    revenue: float = Field(ge=0)
    profit: float = Field(ge=0)
    orders: int = Field(ge=0)


VALID_MONTHS = {
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
}


@app.post("/api/sales")
def create_or_update_sale(sale: SaleInput):
    """Add a new month's sales or update an existing month."""
    month = sale.month.strip().title()

    if month not in VALID_MONTHS:
        raise HTTPException(
            status_code=400,
            detail="Month must be a valid three-letter month, e.g. Jan.",
        )

    return save_sale(
        month=month,
        revenue=sale.revenue,
        profit=sale.profit,
        orders=sale.orders,
    )


@app.post("/api/sales/import")
def import_sales(sales: list[SaleInput]):
    """Import multiple sales records from a CSV upload."""
    if not sales:
        raise HTTPException(
            status_code=400,
            detail="The uploaded CSV contains no sales records.",
        )

    normalized_sales = []

    for sale in sales:
        month = sale.month.strip().title()

        if month not in VALID_MONTHS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid month: {sale.month}",
            )

        normalized_sales.append(
            {
                "month": month,
                "revenue": sale.revenue,
                "profit": sale.profit,
                "orders": sale.orders,
            }
        )

    # Prevent duplicate months within the same CSV.
    month_names = [sale["month"] for sale in normalized_sales]

    if len(month_names) != len(set(month_names)):
        raise HTTPException(
            status_code=400,
            detail="The CSV contains duplicate months.",
        )

    return import_sales_data(normalized_sales)

@app.get("/api/predictions/revenue")
def revenue_prediction():
    """Predict revenue from historical sales data."""
    sales = get_all_sales()

    if len(sales) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two months of sales data are required.",
        )

    try:
        return predict_next_revenue(sales)
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

@app.get("/api/insights")
def get_sales_insights():
    sales = get_all_sales()

    try:
        return generate_sales_insights(sales)
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to generate sales insights: {error}",
        ) from error
