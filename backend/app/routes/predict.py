"""Prediction endpoints (real ML only; there is no fake prediction path)."""
from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from ..schemas import PredictRecords, PredictResponse

router = APIRouter(prefix="/api")


@router.post("/predict", response_model=PredictResponse, tags=["predict"])
async def predict_csv(request: Request, file: UploadFile = File(...)):
    """Score a CSV whose columns exactly match the trained feature schema."""
    st = request.app.state
    st.model.require()  # raises ModelUnavailable -> 503 envelope
    raw = await file.read(st.settings.max_upload_bytes + 1)
    if len(raw) > st.settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File is too large.")
    if not raw.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        df = pd.read_csv(io.StringIO(raw.decode("utf-8-sig")), low_memory=False)
    except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse the file as UTF-8 CSV: {exc}")
    return st.model.predict_frame(df)


@router.post("/predict/records", response_model=PredictResponse, tags=["predict"])
def predict_records(body: PredictRecords, request: Request):
    return request.app.state.model.predict_frame(pd.DataFrame(body.samples))
