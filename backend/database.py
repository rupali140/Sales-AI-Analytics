
import sqlite3
from pathlib import Path

# Project directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "sales.db"

# Create data folder if it does not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection():
    """Create and return a SQLite database connection."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create the sales table and insert initial sample data."""
    sample_sales = [
        ("Jan", 12000, 3000, 25),
        ("Feb", 15000, 4200, 30),
        ("Mar", 13500, 3500, 28),
        ("Apr", 18000, 5000, 36),
        ("May", 22000, 6200, 42),
        ("Jun", 19500, 5400, 39),
        ("Jul", 24000, 7000, 46),
        ("Aug", 26000, 7600, 50),
        ("Sep", 23000, 6500, 45),
        ("Oct", 28000, 8200, 55),
        ("Nov", 32000, 9500, 62),
        ("Dec", 35000, 10500, 68),
    ]

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT NOT NULL UNIQUE,
                revenue REAL NOT NULL,
                profit REAL NOT NULL,
                orders INTEGER NOT NULL
            )
            """
        )

        count = connection.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()[0]

        if count == 0:
            connection.executemany(
                """
                INSERT INTO sales (month, revenue, profit, orders)
                VALUES (?, ?, ?, ?)
                """,
                sample_sales,
            )


def get_all_sales():
    """Fetch all sales records from the database."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT month, revenue, profit, orders
            FROM sales
            ORDER BY id
            """
        ).fetchall()

        return [dict(row) for row in rows]

def save_sale(month, revenue, profit, orders):
    """Insert a new month or update an existing month's sales."""

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO sales (month, revenue, profit, orders)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(month) DO UPDATE SET
                revenue = excluded.revenue,
                profit = excluded.profit,
                orders = excluded.orders
            """,
            (month, revenue, profit, orders),
        )

    return {"message": f"Sales data for {month} saved successfully."}

def import_sales_data(sales):
    """Insert new months and update existing months."""

    with get_connection() as connection:
        existing_months = {
            row["month"]
            for row in connection.execute(
                "SELECT month FROM sales"
            ).fetchall()
        }

        inserted_count = sum(
            1 for sale in sales
            if sale["month"] not in existing_months
        )

        updated_count = len(sales) - inserted_count

        connection.executemany(
            """
            INSERT INTO sales (month, revenue, profit, orders)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(month) DO UPDATE SET
                revenue = excluded.revenue,
                profit = excluded.profit,
                orders = excluded.orders
            """,
            [
                (
                    sale["month"],
                    sale["revenue"],
                    sale["profit"],
                    sale["orders"],
                )
                for sale in sales
            ],
        )

    return {
        "message": "CSV import successful",
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "total_imported": len(sales),
    }
