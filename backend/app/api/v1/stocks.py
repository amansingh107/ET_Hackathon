from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.stock import Stock
from app.models.ohlcv import OHLCVDaily
from app.models.filing import CorporateFiling

router = APIRouter(prefix="/stocks", tags=["stocks"])


class StockOut(BaseModel):
    symbol: str
    company_name: str
    sector: Optional[str]
    industry: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class OHLCVOut(BaseModel):
    time: str
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]


@router.get("", response_model=List[StockOut])
def list_stocks(
    sector: Optional[str] = None,
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(Stock).filter(Stock.is_active == True)
    if sector:
        q = q.filter(Stock.sector == sector)
    return q.limit(limit).all()


@router.get("/{symbol}", response_model=StockOut)
def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock


@router.get("/{symbol}/ohlcv")
def get_ohlcv(
    symbol: str,
    days: int = Query(30, le=365),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(OHLCVDaily)
        .filter(OHLCVDaily.symbol == symbol.upper())
        .order_by(OHLCVDaily.time.desc())
        .limit(days)
        .all()
    )
    return [
        {
            "time": r.time.isoformat(),
            "open": float(r.open) if r.open else None,
            "high": float(r.high) if r.high else None,
            "low": float(r.low) if r.low else None,
            "close": float(r.close) if r.close else None,
            "volume": r.volume,
        }
        for r in rows
    ]


@router.get("/{symbol}/filings")
def get_filings(
    symbol: str,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(CorporateFiling)
        .filter(CorporateFiling.symbol == symbol.upper())
        .order_by(CorporateFiling.filing_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "filing_type": r.filing_type,
            "filing_date": r.filing_date.isoformat(),
            "subject": r.subject,
            "content_url": r.content_url,
            "is_processed": r.is_processed,
        }
        for r in rows
    ]
