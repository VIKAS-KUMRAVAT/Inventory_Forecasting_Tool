from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date

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

class SalesDataBase(BaseModel):
    product: str
    city: str
    date: date
    sales: float

class SalesDataCreate(SalesDataBase):
    pass

class SalesDataList(BaseModel):
    sales: List[SalesDataBase]