from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routers import calculations, tickers
from src.api.db import ensure_table_exists

app = FastAPI(
    title="Irish Capital Gains Calculator API",
    version="1.0.0",
    description="Calculate Irish CGT, ETF exit tax, and dividend income tax from transaction files.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calculations.router)
app.include_router(tickers.router)


@app.on_event("startup")
async def startup():
    try:
        ensure_table_exists()
    except Exception as e:
        print(f"Warning: Could not connect to DynamoDB: {e}")
        print("Calculations will not be persisted until DynamoDB is available.")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
