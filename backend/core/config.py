"""
配置管理模块 - 负责读写和管理系统配置
"""
import json
import os
from datetime import datetime
from typing import Optional
from pathlib import Path

from models.schemas import AppConfig, ProviderType

CONFIG_FILE_PATH = Path(os.getenv("CONFIG_FILE", "./data/config.json"))


def ensure_directories():
    """确保数据目录存在"""
    dirs = ["./data", "./data/uploads", "./data/chroma_db", "./data/conversations"]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config_path = CONFIG_FILE_PATH
    
    def config_exists(self) -> bool:
        """检查配置文件是否存在"""
        return self.config_path.exists()
    
    def create_default_config(self) -> AppConfig:
        """创建默认配置"""
        default_config = AppConfig(
            provider=ProviderType.DEEPSEEK,
            api_key="",
            model="deepseek-chat",
            embedding_model="all-MiniLM-L6-v2",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        self.save_config(default_config)
        return default_config
    
    def load_config(self) -> AppConfig:
        """加载配置"""
        if not self.config_exists():
            return self.create_default_config()
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return AppConfig(**data)
        except Exception as e:
            print(f"加载配置失败: {e}")
            return self.create_default_config()
    
    def save_config(self, config: AppConfig) -> bool:
        """保存配置"""
        try:
            config.updated_at = datetime.now().isoformat()
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config.model_dump(by_alias=False), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置失败: {e}")
            return False
    
    def get_api_key(self) -> Optional[str]:
        """获取API Key"""
        config = self.load_config()
        return config.api_key if config.api_key else None
    
    def get_base_url(self) -> Optional[str]:
        """获取自定义Base URL"""
        config = self.load_config()
        return config.custom_base_url
