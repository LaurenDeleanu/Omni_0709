from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import csv
import io

from app.api.dependencies import get_current_user
from app.services.predictive_analytics import MARKET_BENCHMARKS

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])

@router.post("/upload")
async def upload_benchmarks(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """
    Upload market compensation data as CSV.
    Expected columns: department, market_average, market_median
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
    content = await file.read()
    try:
        csv_file = io.StringIO(content.decode("utf-8"))
        reader = csv.DictReader(csv_file)
        
        count = 0
        for row in reader:
            dept = row.get("department")
            if not dept:
                continue
                
            try:
                avg = float(row.get("market_average", 0))
                med = float(row.get("market_median", 0))
                
                MARKET_BENCHMARKS[dept] = {
                    "market_average": avg,
                    "market_median": med
                }
                count += 1
            except ValueError:
                pass
                
        return {"status": "success", "message": f"Successfully imported {count} benchmarks"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process CSV: {str(e)}")

@router.get("/")
async def get_benchmarks(current_user: dict = Depends(get_current_user)):
    """
    Get current market benchmarks.
    """
    return MARKET_BENCHMARKS
