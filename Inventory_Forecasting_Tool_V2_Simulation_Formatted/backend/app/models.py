from sqlalchemy import Table, Column, Integer, String, Float, Date, ForeignKey
from .database import metadata

users = Table(
    "users",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("email", String, unique=True, index=True, nullable=False),
    Column("hashed_password", String, nullable=False),
    Column("role", String, default="manager")  # 'admin' or 'manager'
)

sales_data = Table(
    "sales_data",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("product", String, index=True, nullable=False),
    Column("city", String, index=True, nullable=False),
    Column("date", Date, nullable=False),
    Column("sales", Float, nullable=False),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),

    # --- Simulation/Scenario columns (all optional, can be used for filtering, analysis, simulation) ---
    Column("discount_pct", Float, nullable=True),           # Percentage discount applied
    Column("seasonality", String, nullable=True),           # E.g., "summer", "winter"
    Column("is_holiday", Integer, nullable=True),           # 1=holiday, 0=not holiday
    Column("weather_condition", String, nullable=True)      # E.g., "rainy", "sunny", etc.
)
