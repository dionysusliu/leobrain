from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from common.database import get_session
from common.models import AnalysisResult, AnalysisResultBase

router = APIRouter()


@router.get("/", response_model=List[AnalysisResult])
def get_analysis_results(
    content_id: int = None,
    plugin: str = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)  
):
    """Get analysis results with optional filtering"""
    statement = select(AnalysisResult)
    if content_id:
        statement = statement.where(AnalysisResult.content_id == content_id)
    if plugin:
        statement = statement.where(AnalysisResult.plugin == plugin)
    statement = statement.offset(skip).limit(limit)
    results = session.exec(statement).all()
    
    return results


@router.post("/", response_model=AnalysisResult)
def create_analysis_result(
    result: AnalysisResultBase,
    session: Session = Depends(get_session)
):
    """Create a new analysis result"""
    db_result = AnalysisResult(**result.model_dump())
    session.add(db_result)
    session.commit()
    session.refresh(db_result)
    return db_result