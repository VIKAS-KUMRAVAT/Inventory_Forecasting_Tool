from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from . import models, database, crud, auth
from .schemas import UserCreate, Token
from .forecast import router as forecast_router
from databases import Database
from fastapi import UploadFile, File
from sqlalchemy import delete
from app.models import sales_data
from app.database import database
import io
import pandas as pd


app = FastAPI(title="Inventory Forecasting API")

# CORS middleware to allow frontend requests from React dev server on localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # change if your frontend runs on a different origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router, tags=["forecast"])

@app.on_event("startup")
async def startup():
    await database.connect()
    # Create tables here if needed
    # await database.metadata.create_all(bind=database.engine)  # For synchronous engine

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
        # Attempt CSV first
        df = pd.read_csv(io.BytesIO(contents))
    except Exception:
        try:
            df = pd.read_excel(io.BytesIO(contents))
        except Exception:
            raise HTTPException(status_code=400, detail="File must be CSV or Excel")

    # Validate columns
    required_cols = {'product', 'city', 'date', 'sales'}
    if not required_cols.issubset(df.columns):
        raise HTTPException(status_code=400, detail=f"Data missing required columns: {required_cols}")

    # Convert 'date' column to datetime
    try:
        df['date'] = pd.to_datetime(df['date']).dt.date
    except ValueError:
        # Try parsing with dayfirst if ValueError
        df['date'] = pd.to_datetime(df['date'], dayfirst=True).dt.date

    # DELETE existing sales_data rows for this user
    delete_query = sales_data.delete().where(sales_data.c.user_id == user_id)
    await database.execute(delete_query)

    # Prepare rows for DB insertion
    data_rows = df.to_dict(orient='records')

    await crud.add_sales_data(data_rows, user_id)

    return {"msg": f"Uploaded {len(data_rows)} sales rows"}


# --- New endpoint added below ---

@app.get("/available-options/")
async def available_options(token: str = Depends(auth.oauth2_scheme)):
    """
    Returns the unique products and cities for the logged-in user 
    based on their uploaded sales data.
    """
    token_data = auth.decode_access_token(token)
    user_id = int(token_data['user_id'])

    products = await crud.get_unique_products(user_id)
    cities = await crud.get_unique_cities(user_id)

    return {"products": products, "cities": cities}
