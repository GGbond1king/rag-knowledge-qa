"""
健康检查API
"""
from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "RAG智能检索系统",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
