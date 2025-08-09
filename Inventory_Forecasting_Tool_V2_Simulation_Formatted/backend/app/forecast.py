from fastapi import APIRouter, Depends, HTTPException, Body
import pandas as pd
from prophet import Prophet
from .crud import get_sales_data
from .auth import oauth2_scheme, decode_access_token
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    token_data = decode_access_token(token)
    return token_data

class SimulationParams(BaseModel):
    discount_pct: Optional[float] = 0.0       # e.g., 10.0 for 10%
    seasonality: Optional[str] = None         # e.g., "high", "low", "summer", "winter"
    is_holiday: Optional[int] = 0              # 0 or 1, default no holiday
    weather_condition: Optional[str] = None   # e.g., "sunny", "rainy", "snowy"

@router.post("/forecast/")
async def forecast(
    product: str,
    city: str,
    days: int = 30,
    simulation_params: SimulationParams = Body(...),
    token: str = Depends(oauth2_scheme)
):
    token_data = decode_access_token(token)
    user_id = int(token_data["user_id"])

    sales_rows = await get_sales_data(product, city, user_id)
    if not sales_rows:
        raise HTTPException(status_code=404, detail="No sales data found for product/city.")

    rows = [dict(row) for row in sales_rows]

    df = pd.DataFrame(rows or [])
    if df.empty or 'date' not in df.columns or 'sales' not in df.columns:
        raise HTTPException(status_code=400, detail="Sales data missing or invalid for the selection")

    df = df.rename(columns={"date": "ds", "sales": "y"})
    df['ds'] = pd.to_datetime(df['ds'])

    # Prepare columns for new regressors with default historical values (assumed 0 or base level)
    # Extend as needed for actual historical regressor data if available

    # Discount - default 0 (no discount historically)
    df['discount_pct'] = 0.0
    # Holiday - default 0 (no holiday historically)
    df['is_holiday'] = 0

    # Seasonality and Weather are categorical, encode with dummy variables
    # Create dummy columns for example categories (extend with your categories as needed)
    seasonality_categories = ['high', 'low', 'summer', 'winter', 'spring', 'fall']
    weather_categories = ['sunny', 'rainy', 'snowy', 'cloudy']

    for cat in seasonality_categories:
        col_name = f"seasonality_{cat}"
        df[col_name] = 0

    for cat in weather_categories:
        col_name = f"weather_{cat}"
        df[col_name] = 0

    # Initialize Prophet model and add all regressors
    m = Prophet()
    m.add_regressor('discount_pct')
    m.add_regressor('is_holiday')
    for cat in seasonality_categories:
        m.add_regressor(f"seasonality_{cat}")
    for cat in weather_categories:
        m.add_regressor(f"weather_{cat}")

    # Fit the model with historical data
    m.fit(df)

    # Create a future dataframe for the forecast period
    future = m.make_future_dataframe(periods=days)

    # Populate the regressor columns in future dataframe with simulation inputs
    future['discount_pct'] = simulation_params.discount_pct if simulation_params.discount_pct is not None else 0.0
    future['is_holiday'] = simulation_params.is_holiday if simulation_params.is_holiday is not None else 0

    # Set all seasonality and weather dummy columns to 0 initially
    for cat in seasonality_categories:
        future[f"seasonality_{cat}"] = 0
    for cat in weather_categories:
        future[f"weather_{cat}"] = 0

    # Mark the selected seasonality and weather category as 1 if provided and valid
    if simulation_params.seasonality and simulation_params.seasonality.lower() in seasonality_categories:
        future[f"seasonality_{simulation_params.seasonality.lower()}"] = 1

    if simulation_params.weather_condition and simulation_params.weather_condition.lower() in weather_categories:
        future[f"weather_{simulation_params.weather_condition.lower()}"] = 1

    # Predict the future with regressors applied
    forecast_df = m.predict(future)

    # Return only the forecast for the requested days (last 'days' rows)
    result = forecast_df[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(days).to_dict(orient='records')

    return {"forecast": result}
