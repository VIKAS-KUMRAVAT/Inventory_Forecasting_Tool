from .models import users, sales_data
from .schemas import UserCreate
from .auth import get_password_hash
from .database import database
from sqlalchemy import and_, select, distinct
from typing import Optional, List


async def get_user_by_email(email: str):
    query = users.select().where(users.c.email == email)
    return await database.fetch_one(query)


async def create_user(user: UserCreate):
    hashed_password = get_password_hash(user.password)
    query = users.insert().values(
        email=user.email,
        hashed_password=hashed_password,
        role=user.role
    )
    user_id = await database.execute(query)
    return {"id": user_id, "email": user.email, "role": user.role}


async def authenticate_user(email: str, password: str):
    user = await get_user_by_email(email)
    if not user:
        return False
    from .auth import verify_password
    if not verify_password(password, user['hashed_password']):
        return False
    return user


async def add_sales_data(data_rows: List[dict], user_id: int):
    # Allowed columns for the sales_data table — update if you add more to models.py
    allowed_columns = {
        "product",
        "city",
        "date",
        "sales",
        "user_id",
        "discount_pct",
        "seasonality",
        "is_holiday",
        "weather_condition",
    }
    query = sales_data.insert()
    for row in data_rows:
        # Always set 'user_id'
        row_to_insert = {k: v for k, v in row.items() if k in allowed_columns}
        row_to_insert["user_id"] = user_id
        await database.execute(query.values(**row_to_insert))


async def get_sales_data(product: str, city: str, user_id: int):
    query = sales_data.select().where(
        and_(
            sales_data.c.product == product,
            sales_data.c.city == city,
            sales_data.c.user_id == user_id
        )
    )
    return await database.fetch_all(query)


# ------------------------
# New and improved methods
# ------------------------

async def get_all_sales_data(user_id: int):
    """
    Return all sales data rows for a given user.
    """
    query = sales_data.select().where(sales_data.c.user_id == user_id)
    return await database.fetch_all(query)


async def get_unique_products(user_id: int):
    query = select(distinct(sales_data.c.product)).where(sales_data.c.user_id == user_id)
    rows = await database.fetch_all(query)
    return [row[0] for row in rows]


async def get_unique_cities(user_id: int):
    query = select(distinct(sales_data.c.city)).where(sales_data.c.user_id == user_id)
    rows = await database.fetch_all(query)
    return [row[0] for row in rows]


async def get_unique_field_values(user_id: int, fieldname: str):
    """
    Returns unique values for any column in the sales_data table for this user's data.
    Usage example: await get_unique_field_values(user_id, "seasonality")
    """
    # Defensive: only allow valid columns to prevent SQL injection
    allowed_cols = {"product", "city", "seasonality", "weather_condition", "is_holiday", "discount_pct", "date", "sales"}
    if fieldname not in allowed_cols:
        raise ValueError(f"Field {fieldname} is not allowed.")

    t = getattr(sales_data.c, fieldname)
    query = select(distinct(t)).where(sales_data.c.user_id == user_id)
    rows = await database.fetch_all(query)
    # Return cleaned-up list, removing None values
    return sorted([row[0] for row in rows if row[0] is not None])

