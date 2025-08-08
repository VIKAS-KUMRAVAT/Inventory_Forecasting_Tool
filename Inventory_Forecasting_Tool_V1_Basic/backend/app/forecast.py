from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
import pandas as pd
from prophet import Prophet
from datetime import timedelta
from .crud import get_sales_data
from .schemas import SalesDataBase
from .auth import oauth2_scheme, decode_access_token

router = APIRouter()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    token_data = decode_access_token(token)
    return token_data

@router.post("/forecast/")
async def forecast(
    product: str,
    city: str,
    days: int = 30,
    token: str = Depends(oauth2_scheme)
):
    token_data = decode_access_token(token)
    user_id = int(token_data["user_id"])

   
    
    sales_rows = await get_sales_data(product, city, user_id)
    if not sales_rows:
        raise HTTPException(status_code=404, detail="No sales data found for product/city.")
    
    # Convert sales_rows (list of Record) to list of dicts
    rows = [dict(row) for row in sales_rows]
    
    
    # Convert to DataFrame for Prophet
   
    df = pd.DataFrame(rows or [])
    if df.empty or 'date' not in df.columns or 'sales' not in df.columns:
        raise HTTPException(status_code=400, detail="Sales data missing or invalid for the selection")
    df = df.rename(columns={"date": "ds", "sales": "y"})
    df['ds'] = pd.to_datetime(df['ds'])

    
    m = Prophet()
    m.fit(df)

    future = m.make_future_dataframe(periods=days)
    forecast_df = m.predict(future)

    # Return key columns as list of dicts
    result = forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days).to_dict(orient='records')
    return {"forecast": result}
