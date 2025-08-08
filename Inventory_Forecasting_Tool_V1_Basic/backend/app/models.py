from sqlalchemy import Table, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
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
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False)
)