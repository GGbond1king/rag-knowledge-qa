"""
RAG智能检索系统 - FastAPI后端主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from api import config, documents, chat, health
from core.config import ConfigManager, ensure_directories

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    ensure_directories()
    config_manager = ConfigManager()
    if not config_manager.config_exists():
        config_manager.create_default_config()

    # 清理上次残留的"处理中"文档（服务重启后任务已丢失）
    try:
        import json
        meta_path = "./data/documents_meta.json"
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            changed = False
            for doc_id, doc in meta.items():
                if doc.get('status') == 'processing':
                    doc['status'] = 'failed'
                    doc['error_message'] = '服务重启，处理任务已取消，请重新上传'
                    changed = True
            if changed:
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
                print("[Startup] 已清理残留的 processing 文档")
    except Exception as e:
        print(f"[Startup] 清理失败: {e}")

    yield


app = FastAPI(
    title="RAG智能检索系统",
    description="基于检索增强生成（RAG）技术的智能问答系统",
    version="1.0.0",
    lifespan=lifespan
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGINS", "http://localhost:5173")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api", tags=["健康检查"])
app.include_router(config.router, prefix="/api", tags=["配置管理"])
app.include_router(documents.router, prefix="/api", tags=["文档管理"])
app.include_router(chat.router, prefix="/api", tags=["智能对话"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
