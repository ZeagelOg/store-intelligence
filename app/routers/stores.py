from fastapi import APIRouter

router = APIRouter()

@router.get("/{store_id}/metrics")
async def metrics(store_id: str):
    return {
        "store_id": store_id,
        "unique_visitors": 42,
        "conversion_rate": 0.23,
        "current_queue_depth": 3,
        "abandonment_rate": 0.12
    }

@router.get("/{store_id}/funnel")
async def funnel(store_id: str):
    return {
        "stages": [
            {"stage": "Entry", "count": 100, "drop_off_pct": 0},
            {"stage": "Zone", "count": 75, "drop_off_pct": 25},
            {"stage": "Billing", "count": 50, "drop_off_pct": 33},
            {"stage": "Purchase", "count": 23, "drop_off_pct": 54}
        ]
    }

@router.get("/{store_id}/heatmap")
async def heatmap(store_id: str):
    return {"zones": []}

@router.get("/{store_id}/anomalies")
async def anomalies(store_id: str):
    return {"anomalies": []}
