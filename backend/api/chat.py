"""
智能对话API - RAG问答与流式响应
"""
import os
import uuid
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.retriever import get_rag_pipeline
from models.schemas import MessageModel, MessageRole, AnswerMode, ConversationModel

router = APIRouter()

# 全局RAG管道实例（延迟初始化）
_rag_pipeline_instance = None


# 对话历史存储目录
CONVERSATIONS_DIR = "./data/conversations"


def ensure_conversations_dir():
    """确保对话目录存在"""
    os.makedirs(CONVERSATIONS_DIR, exist_ok=True)


def _load_conversation(conv_id: str) -> Optional[dict]:
    """加载对话数据"""
    filepath = f"{CONVERSATIONS_DIR}/{conv_id}.json"
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def _save_conversation(conv_data: dict):
    """保存对话数据"""
    ensure_conversations_dir()
    filepath = f"{CONVERSATIONS_DIR}/{conv_data['id']}.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(conv_data, f, indent=2, ensure_ascii=False)


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    use_web_search: Optional[bool] = None


@router.post("/chat/message")
async def chat_message(request: ChatRequest):
    """
    发送消息并进行RAG问答
    
    返回Server-Sent Events流式响应
    """
    global _rag_pipeline_instance
    if _rag_pipeline_instance is None:
        _rag_pipeline_instance = get_rag_pipeline()
    
    # 加载或创建对话
    conv_id = request.conversation_id
    if conv_id:
        conversation = _load_conversation(conv_id)
        if not conversation:
            # 如果对话ID不存在，创建新对话
            conv_id = str(uuid.uuid4())
            conversation = {
                "id": conv_id,
                "title": request.message[:30] + ("..." if len(request.message) > 30 else ""),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "message_count": 0,
                "messages": []
            }
    else:
        conv_id = str(uuid.uuid4())
        conversation = {
            "id": conv_id,
            "title": request.message[:30] + ("..." if len(request.message) > 30 else ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "message_count": 0,
            "messages": []
        }
    
    # 添加用户消息到历史
    user_msg = {
        "id": str(uuid.uuid4()),
        "role": MessageRole.USER.value,
        "content": request.message,
        "timestamp": datetime.now().isoformat(),
        "sources": None,
        "search_results": None,
        "mode": None
    }
    conversation['messages'].append(user_msg)
    conversation['message_count'] += 1
    
    # 转换历史消息格式
    history_msgs = [
        MessageModel(**msg) for msg in conversation.get('messages', [])
    ]
    
    async def generate():
        """流式生成器"""
        full_content = ""
        sources = []
        search_results = []
        mode = AnswerMode.LOCAL.value
        
        try:
            async for result in _rag_pipeline_instance.query(request, history_msgs):
                token_data = result.get('token', '')
                full_content += token_data
                
                if result.get('sources'):
                    sources = result['sources']
                if result.get('search_results'):
                    search_results = result['search_results']
                if result.get('mode'):
                    mode = result['mode']
                
                # 发送SSE事件
                yield f"data: {json.dumps({'token': token_data, 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"
            
            # 流结束标记
            yield f"data: [DONE]\n\n"
            
        except Exception as e:
            error_msg = f"处理出错: {str(e)}"
            full_content = error_msg
            yield f"data: {json.dumps({'error': error_msg}, ensure_ascii=False)}\n\n"
        
        finally:
            # 保存助手回复到对话历史
            assistant_msg = {
                "id": str(uuid.uuid4()),
                "role": MessageRole.ASSISTANT.value,
                "content": full_content,
                "timestamp": datetime.now().isoformat(),
                "sources": [s if isinstance(s, dict) else s.model_dump() for s in sources],
                "search_results": search_results,
                "mode": mode
            }
            conversation['messages'].append(assistant_msg)
            conversation['message_count'] += 1
            conversation['updated_at'] = datetime.now().isoformat()
            _save_conversation(conversation)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/chat/history")
async def get_chat_history():
    """获取所有对话历史列表"""
    ensure_conversations_dir()
    
    conversations = []
    for filename in os.listdir(CONVERSATIONS_DIR):
        if filename.endswith('.json'):
            filepath = f"{CONVERSATIONS_DIR}/{filename}"
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    conv = json.load(f)
                    conversations.append({
                        "id": conv.get('id'),
                        "title": conv.get('title', '未命名对话'),
                        "created_at": conv.get('created_at'),
                        "updated_at": conv.get('updated_at'),
                        "message_count": conv.get('message_count', 0)
                    })
            except:
                continue
    
    # 按更新时间倒序
    conversations.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    
    return {
        "success": True,
        "data": conversations,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/chat/history/{conv_id}")
async def get_conversation_detail(conv_id: str):
    """获取指定对话的详细内容"""
    conversation = _load_conversation(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    return {
        "success": True,
        "data": conversation,
        "timestamp": datetime.now().isoformat()
    }


@router.put("/chat/history/{conv_id}/rename")
async def rename_conversation(conv_id: str, body: dict):
    """重命名对话"""
    conversation = _load_conversation(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    new_title = body.get("title", "").strip()
    if not new_title:
        raise HTTPException(status_code=400, detail="标题不能为空")

    conversation["title"] = new_title
    conversation["updated_at"] = datetime.now().isoformat()
    _save_conversation(conversation)

    return {
        "success": True,
        "data": {"id": conv_id, "title": new_title},
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/chat/history/{conv_id}")
async def delete_conversation(conv_id: str):
    """删除指定对话"""
    filepath = f"{CONVERSATIONS_DIR}/{conv_id}.json"
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="对话不存在")

    os.remove(filepath)

    return {
        "success": True,
        "data": {"message": "对话已删除"},
        "timestamp": datetime.now().isoformat()
    }


@router.post("/chat/history/{conv_id}/export")
async def export_conversation(conv_id: str):
    """导出对话为Markdown格式"""
    from fastapi.responses import Response
    
    conversation = _load_conversation(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    
    # 生成Markdown内容
    lines = [f"# {conversation.get('title', '对话记录')}\n"]
    lines.append(f"**创建时间**: {conversation.get('created_at', '')}\n")
    lines.append("---\n")
    
    for msg in conversation.get('messages', []):
        role = "👤 用户" if msg.get('role') == 'user' else "🤖 助手"
        lines.append(f"## {role}\n")
        lines.append(f"{msg.get('content', '')}\n")
        
        # 显示来源引用
        if msg.get('sources'):
            lines.append("\n**参考来源:**\n")
            for src in msg['sources']:
                src_name = src.get('document_name', '') if isinstance(src, dict) else src.document_name
                lines.append(f"- {src_name}\n")
        
        # 显示搜索结果
        if msg.get('search_results'):
            lines.append("\n**网络搜索来源:**\n")
            for sr in msg['search_results']:
                sr_data = sr if isinstance(sr, dict) else sr.model_dump()
                lines.append(f"- [{sr_data.get('title', '')}]({sr_data.get('url', '')})\n")
        
        lines.append("\n---\n")
    
    markdown_content = "\n".join(lines)
    
    return Response(
        content=markdown_content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename=conversation_{conv_id}.md"}
    )
