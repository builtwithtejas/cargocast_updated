from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline import (
    get_forecast,
    get_recommendation,
    run_scenario,
    estimate_savings,
)

app = FastAPI(title="CargoCast API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


ROUTE = "Vizag-Capesize-IronOre"


class ScenarioRequest(BaseModel):
    fuel_pct_change: float = 0.0
    delay_days: float = 0.0
    demand_shock_pct: float = 0.0


@app.get("/")
def root():
    return {
        "name": "CargoCast API",
        "status": "online",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/forecast")
def api_forecast(
    horizon_days: int = Query(60, ge=7, le=180)
):
    df = get_forecast(
        ROUTE,
        horizon_days=horizon_days
    )

    return {
        "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
        "forecast": df["forecast"].round(2).tolist(),
        "lower": df["lower"].round(2).tolist(),
        "upper": df["upper"].round(2).tolist(),
    }


@app.get("/api/recommendation")
def api_recommendation(
    horizon_days: int = Query(60, ge=7, le=180)
):
    return get_recommendation(
        ROUTE,
        horizon_days=horizon_days
    )


@app.post("/api/scenario")
def api_scenario(
    request: ScenarioRequest,
    horizon_days: int = Query(60, ge=7, le=180)
):
    scenario_params = {
        "fuel_price_pct_change": request.fuel_pct_change,
        "delay_days": request.delay_days,
        "demand_shock_pct": request.demand_shock_pct,
    }

    result = run_scenario(
        ROUTE,
        horizon_days,
        scenario_params,
    )

    base_df = get_forecast(
        ROUTE,
        horizon_days=horizon_days
    )

    from .pipeline import _apply_scenario

    scenario_df = _apply_scenario(
        base_df,
        scenario_params,
    )

    savings = estimate_savings(
        ROUTE,
        lookback_days=90
    )

    return {
        "base_forecast": {
            "dates": base_df["date"].dt.strftime("%Y-%m-%d").tolist(),
            "forecast": base_df["forecast"].round(2).tolist(),
            "lower": base_df["lower"].round(2).tolist(),
            "upper": base_df["upper"].round(2).tolist(),
        },
        "scenario_forecast": {
            "dates": scenario_df["date"].dt.strftime("%Y-%m-%d").tolist(),
            "forecast": scenario_df["forecast"].round(2).tolist(),
            "lower": scenario_df["lower"].round(2).tolist(),
            "upper": scenario_df["upper"].round(2).tolist(),
        },
        "recommendation": result,
        "savings": savings,
    }


@app.get("/api/savings")
def api_savings():
    return estimate_savings(
        ROUTE,
        lookback_days=90
    )
