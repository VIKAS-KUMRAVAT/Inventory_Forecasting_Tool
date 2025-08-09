from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date

# --- User & Authentication ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "manager"

class User(BaseModel):
    id: int
    email: EmailStr
    role: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Sales Data Schemas ---

class SalesDataBase(BaseModel):
    product: str
    city: str
    date: date
    sales: float

    # --- New scenario/simulation fields (all optional) ---
    discount_pct: Optional[float] = None
    seasonality: Optional[str] = None
    is_holiday: Optional[int] = None
    weather_condition: Optional[str] = None

class SalesDataCreate(SalesDataBase):
    pass

class SalesDataList(BaseModel):
    sales: List[SalesDataBase]

# --- Simulation Params for forecast API ---

class SimulationParams(BaseModel):
    discount_pct: Optional[float] = 0.0             # e.g., 10% discount
    seasonality: Optional[str] = None                # e.g., 'summer'
    is_holiday: Optional[int] = 0                    # 1 if holiday, else 0
    weather_condition: Optional[str] = None          # e.g., 'sunny'

# (Optional) If you want to structure the available-options response:
class AvailableOptions(BaseModel):
    products: List[str]
    cities: List[str]
    seasonality: List[str]
    weather: List[str]
    holiday: List[int]
    default_simulation: SimulationParams
