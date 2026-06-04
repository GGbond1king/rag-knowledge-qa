"""
配置管理API
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from core.config import ConfigManager
from models.schemas import AppConfig, ApiResponse

router = APIRouter()
config_manager = ConfigManager()


@router.get("/config")
async def get_config():
    """获取当前系统配置"""
    try:
        config = config_manager.load_config()
        return {
            "success": True,
            "data": config.model_dump(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_config(config: AppConfig):
    """更新系统配置"""
    try:
        success = config_manager.save_config(config)
        if success:
            return {
                "success": True,
                "data": config.model_dump(),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="保存配置失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
