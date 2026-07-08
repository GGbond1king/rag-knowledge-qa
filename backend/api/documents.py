"""
文档管理API - 文件上传、列表、删除
"""
import os
import uuid
import shutil
import asyncio
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query

from core.config import ConfigManager, ensure_directories
from core.retriever import get_rag_pipeline
from models.schemas import DocumentModel, FileType, DocumentStatus, ApiResponse

router = APIRouter()
config_manager = ConfigManager()

# 文档元数据存储路径
DOCUMENTS_META_FILE = "./data/documents_meta.json"


def _load_documents_meta() -> dict:
    """加载文档元数据"""
    if not os.path.exists(DOCUMENTS_META_FILE):
        return {}
    try:
        import json
        with open(DOCUMENTS_META_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def _save_documents_meta(meta: dict):
    """保存文档元数据"""
    import json
    with open(DOCUMENTS_META_FILE, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def _detect_file_type(filename: str) -> FileType:
    """检测文件类型"""
    ext = os.path.splitext(filename)[1].lower()
    type_map = {".txt": FileType.TXT, ".pdf": FileType.PDF, ".docx": FileType.DOCX}
    return type_map.get(ext, FileType.TXT)


@router.post("/documents/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件并自动进行向量化处理
    
    支持的格式: TXT, PDF, DOCX
    最大文件大小: 50MB
    """
    # 验证文件类型
    allowed_types = {".txt", ".pdf", ".docx"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}。支持的格式: TXT, PDF, DOCX"
        )
    
    # 验证文件大小 (50MB限制)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件大小超过50MB限制")
    
    # 确保上传目录存在
    ensure_directories()
    
    # 生成唯一文件名
    doc_id = str(uuid.uuid4())
    safe_filename = f"{doc_id}{file_ext}"
    upload_path = f"./data/uploads/{safe_filename}"
    
    # 保存文件
    with open(upload_path, 'wb') as f:
        f.write(content)
    
    # 创建文档记录（先存为处理中，防止重复上传）
    file_type = _detect_file_type(file.filename)
    document = DocumentModel(
        id=doc_id,
        filename=safe_filename,
        original_name=file.filename,
        file_type=file_type,
        file_size=len(content),
        upload_time=datetime.now().isoformat(),
        status=DocumentStatus.PROCESSING
    )
    meta = _load_documents_meta()
    meta[doc_id] = document.model_dump()
    _save_documents_meta(meta)

    # 同步处理文档（解析→分块→向量化），调用方等待完成
    try:
        pipeline = get_rag_pipeline()
        chunk_count, source_id = await pipeline.process_uploaded_file(upload_path, file.filename)

        # 更新状态为已索引
        if doc_id in meta:
            meta[doc_id]['status'] = DocumentStatus.INDEXED.value
            meta[doc_id]['chunk_count'] = chunk_count
            _save_documents_meta(meta)

        # 后台构建知识图谱（不阻塞上传响应）
        try:
            asyncio.create_task(_build_graph_async(pipeline, source_id, file.filename))
        except Exception:
            pass

        return {
            "success": True,
            "data": {**document.model_dump(), "status": DocumentStatus.INDEXED.value, "chunk_count": chunk_count},
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"文档处理失败 [{doc_id}]: {e}")
        if doc_id in meta:
            meta[doc_id]['status'] = DocumentStatus.FAILED.value
            meta[doc_id]['error_message'] = str(e)
            _save_documents_meta(meta)
        raise HTTPException(status_code=500, detail=f"文档处理失败: {str(e)}")


async def _build_graph_async(pipeline, source_id: str, original_name: str):
    """后台构建知识图谱"""
    try:
        await pipeline.build_graph_index(source_id, original_name)
    except Exception as e:
        print(f"[GraphRAG] 后台索引失败: {e}")


@router.get("/documents")
async def list_documents():
    """获取已上传的文档列表"""
    meta = _load_documents_meta()
    documents = []
    
    for doc_id, doc_data in meta.items():
        documents.append(doc_data)
    
    # 按上传时间倒序排列
    documents.sort(key=lambda x: x.get('upload_time', ''), reverse=True)
    
    return {
        "success": True,
        "data": documents,
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除指定文档及其向量数据"""
    meta = _load_documents_meta()
    
    if doc_id not in meta:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    doc_data = meta[doc_id]
    
    # 删除物理文件
    filename = doc_data.get('filename', '')
    if filename:
        file_path = f"./data/uploads/{filename}"
        if os.path.exists(file_path):
            os.remove(file_path)
    
    # 删除向量数据
    try:
        pipeline = get_rag_pipeline()
        pipeline.delete_document_from_db(doc_id)
    except Exception as e:
        print(f"删除向量数据失败: {e}")
    
    # 删除元数据记录
    del meta[doc_id]
    _save_documents_meta(meta)
    
    return {
        "success": True,
        "data": {"message": "文档已删除"},
        "timestamp": datetime.now().isoformat()
    }


@router.get("/documents/stats")
async def get_documents_stats():
    """获取知识库统计信息"""
    meta = _load_documents_meta()
    
    total_files = len(meta)
    total_chunks = sum(doc.get('chunk_count', 0) for doc in meta.values())
    indexed_count = sum(1 for doc in meta.values() if doc.get('status') == DocumentStatus.INDEXED.value)
    
    # 获取向量数据库统计
    try:
        pipeline = get_rag_pipeline()
        db_stats = pipeline.retriever.get_stats()
    except:
        db_stats = {"total_chunks": 0}
    
    return {
        "success": True,
        "data": {
            "total_files": total_files,
            "indexed_files": indexed_count,
            "total_chunks": total_chunks or db_stats.get("total_chunks", 0),
            "db_total_chunks": db_stats.get("total_chunks", 0)
        },
        "timestamp": datetime.now().isoformat()
    }
