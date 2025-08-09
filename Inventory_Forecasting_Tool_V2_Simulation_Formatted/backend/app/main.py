from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from . import models, crud, auth
from .schemas import UserCreate, Token
from .forecast import router as forecast_router
from app.models import sales_data
from app.database import database, engine, metadata
from sqlalchemy import inspect, text
import io
import pandas as pd

app = FastAPI(title="Inventory Forecasting API")

# Allow CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router, tags=["forecast"])


# ---------- Auto Schema Upgrade Helper ----------
async def upgrade_schema_if_needed():
    """
    Ensures the sales_data table contains all expected simulation columns.
    Creates the table if it doesn't exist.
    """
    inspector = inspect(engine)

    tables = inspector.get_table_names()
    if "sales_data" not in tables:
        # Table doesn't exist yet — create all tables
        metadata.create_all(bind=engine)
        print("[DB INIT] Created all tables (sales_data missing).")
        return

    # Table exists — check for missing columns
    existing_columns = [col["name"] for col in inspector.get_columns("sales_data")]

    expected_columns = {
        "discount_pct": "FLOAT",
        "seasonality": "VARCHAR",
        "is_holiday": "INTEGER",
        "weather_condition": "VARCHAR",
    }

    with engine.connect() as conn:
        for col_name, col_type in expected_columns.items():
            if col_name not in existing_columns:
                alter_sql = f'ALTER TABLE sales_data ADD COLUMN "{col_name}" {col_type}'
                conn.execute(text(alter_sql))
                print(f"[DB UPGRADE] Added missing column: {col_name}")


@app.on_event("startup")
async def startup():
    await database.connect()
    await upgrade_schema_if_needed()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/register", response_model=dict)
async def register(user: UserCreate):
    existing = await crud.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = await crud.create_user(user)
    return {"msg": "User created", "user": new_user}


@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await crud.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = auth.create_access_token(data={"sub": str(user["id"])})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/upload-sales/")
async def upload_sales(file: UploadFile = File(...), token: str = Depends(auth.oauth2_scheme)):
    token_data = auth.decode_access_token(token)
    user_id = int(token_data['user_id'])
    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(contents))
        except Exception:
            raise HTTPException(status_code=400, detail="File must be CSV or Excel")

    required_cols = {'product', 'city', 'date', 'sales'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Data missing required columns: {required_cols}")

    # Parse date
    try:
        df['date'] = pd.to_datetime(df['date']).dt.date
    except ValueError:
        df['date'] = pd.to_datetime(df['date'], dayfirst=True).dt.date

    # Remove previous data for this user
    delete_query = sales_data.delete().where(sales_data.c.user_id == user_id)
    await database.execute(delete_query)

    # Add new data (simulation columns auto-handled if present)
    data_rows = df.to_dict(orient='records')
    await crud.add_sales_data(data_rows, user_id)

    return {"msg": f"Uploaded {len(data_rows)} sales rows"}


# ---------------------------------------------
# Endpoint: Returns unique simulation options
# ---------------------------------------------
@app.get("/available-options/")
async def available_options(token: str = Depends(auth.oauth2_scheme)):
    """
    Returns unique products, cities, seasonality, weather, holiday values for the user
    to populate frontend dropdowns, after upload.
    """
    token_data = auth.decode_access_token(token)
    user_id = int(token_data['user_id'])

    # Fetch all rows for this user
    all_rows = await crud.get_all_sales_data(user_id)
    if not all_rows:
        return {
            "products": [],
            "cities": [],
            "seasonality": [],
            "weather": [],
            "holiday": [0, 1],
            "default_simulation": {
                "discount_pct": 0.0,
                "seasonality": "",
                "is_holiday": 0,
                "weather_condition": ""
            }
        }

    df = pd.DataFrame([dict(row) for row in all_rows])

    products = sorted(df["product"].dropna().unique().tolist()) if "product" in df else []
    cities = sorted(df["city"].dropna().unique().tolist()) if "city" in df else []

    seasonality_col = next((col for col in df.columns if "season" in col), None)
    weather_col = next((col for col in df.columns if "weather" in col), None)
    holiday_col = next((col for col in df.columns if "holiday" in col), None)
    discount_col = next((col for col in df.columns if "discount" in col), None)

    seasonality = sorted(df[seasonality_col].dropna().unique().tolist()) if seasonality_col else []
    weather = sorted(df[weather_col].dropna().unique().tolist()) if weather_col else []
    holiday = sorted(df[holiday_col].dropna().unique().tolist()) if holiday_col else [0, 1]

    default_simulation = {
        "discount_pct": float(df[discount_col].dropna().iloc[0]) if discount_col and not df[discount_col].dropna().empty else 0.0,
        "seasonality": df[seasonality_col].dropna().iloc[0] if seasonality_col and not df[seasonality_col].dropna().empty else (seasonality[0] if seasonality else ""),
        "is_holiday": int(df[holiday_col].dropna().iloc[0]) if holiday_col and not df[holiday_col].dropna().empty else (holiday[0] if holiday else 0),
        "weather_condition": df[weather_col].dropna().iloc[0] if weather_col and not df[weather_col].dropna().empty else (weather[0] if weather else "")
    }

    return {
        "products": products,
        "cities": cities,
        "seasonality": seasonality,
        "weather": weather,
        "holiday": holiday,
        "default_simulation": default_simulation
    }
