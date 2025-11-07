from fastapi import APIRouter
from app.api.v1 import contents, analysis, crawlers, jobs

router = APIRouter()

router.include_router(contents.router, prefix="/contents", tags=["contents"])
router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
router.include_router(crawlers.router, prefix="/crawlers", tags=["crawlers"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])