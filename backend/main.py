"""CargoCast FastAPI backend for the original Stitch frontend.

Run locally:
    uvicorn backend.main:app --reload --port 8000

Deploy on Render with:
    uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .pipeline import get_forecast, get_recommendation, run_scenario, estimate_savings

app = FastAPI(title="CargoCast API", version="1.0.0")

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
    cargo_tonnage: int = 150_000
    usd_to_inr: float = 83.5


def _pack_forecast(df):
    return {
        "dates": df["date"].dt.strftime("%Y-%m-%d").tolist(),
        "forecast": df["forecast"].round(2).tolist(),
        "lower": df["lower"].round(2).tolist(),
        "upper": df["upper"].round(2).tolist(),
    }


def _frontend_recommendation(rec):
    """Adapt backend.pipeline's contract to the original Stitch frontend."""
    return {
        "charter_type": "Time-Charter" if rec["charter_decision"] == "TIME_CHARTER" else "Spot",
        "timing": "Buy Now" if rec["timing_decision"] == "BUY_NOW" else "Wait",
        "trend_pct": round(
            ((rec["confidence"] if False else 0.0)), 2
        ),
        "disruption_score": rec["disruption_score"],
        "reason": rec["reasoning"],
        "confidence": rec.get("confidence"),
    }


def _recommendation_with_trend(route, horizon_days):
    rec = get_recommendation(route, horizon_days)
    fc = get_forecast(route, horizon_days)
    early = fc["forecast"].iloc[: min(7, len(fc))].mean()
    late = fc["forecast"].iloc[-min(7, len(fc)):].mean()
    trend_pct = ((late - early) / early * 100) if early else 0.0
    out = _frontend_recommendation(rec)
    out["trend_pct"] = round(float(trend_pct), 2)
    return out


@app.get("/")
def root():
    return {"name": "CargoCast API", "status": "online"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/forecast")
def api_forecast(horizon_days: int = Query(60, ge=7, le=180)):
    return _pack_forecast(get_forecast(ROUTE, horizon_days))


@app.get("/api/disruption-score")
def api_disruption_score(horizon_days: int = Query(60, ge=7, le=180)):
    rec = get_recommendation(ROUTE, horizon_days)
    return {"disruption_score": rec["disruption_score"]}


@app.get("/api/recommendation")
def api_recommendation(horizon_days: int = Query(60, ge=7, le=180)):
    return _recommendation_with_trend(ROUTE, horizon_days)


@app.post("/api/scenario")
def api_scenario(
    req: ScenarioRequest,
    horizon_days: int = Query(60, ge=7, le=180),
):
    overrides = {
        "fuel_price_pct_change": req.fuel_pct_change,
        "delay_days": req.delay_days,
        "demand_shock_pct": req.demand_shock_pct,
    }

    base_df = get_forecast(ROUTE, horizon_days)
    result = run_scenario(ROUTE, horizon_days, overrides)

    # backend.pipeline's scenario function returns the updated recommendation;
    # reconstruct the shocked curve using the same internal scenario function.
    from .pipeline import _apply_scenario
    scenario_df = _apply_scenario(base_df, overrides)

    savings = estimate_savings(ROUTE, 90)

    recommendation = {
        "charter_type": "Time-Charter" if result["charter_decision"] == "TIME_CHARTER" else "Spot",
        "timing": "Buy Now" if result["timing_decision"] == "BUY_NOW" else "Wait",
        "trend_pct": round(
            ((scenario_df["forecast"].iloc[-min(7, len(scenario_df)):].mean() - scenario_df["forecast"].iloc[:min(7, len(scenario_df))].mean())
             / scenario_df["forecast"].iloc[:min(7, len(scenario_df))].mean() * 100),
            2,
        ),
        "disruption_score": result["disruption_score"],
        "reason": result["reasoning"],
        "confidence": result.get("confidence"),
    }

    return {
        "base_forecast": _pack_forecast(base_df),
        "scenario_forecast": _pack_forecast(scenario_df),
        "recommendation": recommendation,
        "savings": {
            "naive_cost_usd": savings["naive_cost"],
            "model_cost_usd": savings["optimized_cost"],
            "savings_usd": savings["savings_amount"],
            "savings_inr": savings["savings_amount"] * req.usd_to_inr,
            "savings_pct": savings["savings_pct"],
        },
    }


@app.get("/api/savings")
def api_savings(
    horizon_days: int = Query(60, ge=7, le=180),
    cargo_tonnage: int = 150_000,
    usd_to_inr: float = 83.5,
):
    savings = estimate_savings(ROUTE, 90)
    return {
        "naive_cost_usd": savings["naive_cost"],
        "model_cost_usd": savings["optimized_cost"],
        "savings_usd": savings["savings_amount"],
        "savings_inr": savings["savings_amount"] * usd_to_inr,
        "savings_pct": savings["savings_pct"],
    }
