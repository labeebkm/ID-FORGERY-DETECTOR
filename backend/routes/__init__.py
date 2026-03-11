from fastapi import APIRouter
from .analyze import router as analyze_router

api_router = APIRouter()
api_router.include_router(analyze_router, tags=["analysis"])

__all__ = ["api_router"]
