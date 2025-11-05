from fastapi import APIRouter
from app.api.v1 import contents, analysis

router = APIRouter()

router.include_router(contents.router, prefix="/contents", tags=["contents"])