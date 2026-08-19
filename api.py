from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from analysis_service import analyze_stock

app = FastAPI(title="Mind Market AI API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/analyze/{ticker}")
def analyze(ticker: str, timeframe: str = Query(default="3M", pattern="^(1M|3M|6M|1Y|2Y)$")) -> dict:
    try:
        return analyze_stock(ticker, timeframe)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=502, detail="Market data provider failed. Please try again.") from error
