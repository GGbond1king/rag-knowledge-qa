"""
核心数据类型定义
"""
from typing import Optional, List
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ProviderType(str, Enum):
    OPENAI = "openai"
    QWEN = "qwen"
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"


class FileType(str, Enum):
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"


class DocumentStatus(str, Enum):
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


class AnswerMode(str, Enum):
    LOCAL = "local"
    WEB = "web"
    HYBRID = "hybrid"


# ====== 配置相关 ======
class AppConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: ProviderType = ProviderType.DEEPSEEK
    api_key: str = Field(default="", alias="apiKey")
    model: str = "deepseek-chat"
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="embeddingModel")
    custom_base_url: Optional[str] = Field(default=None, alias="customBaseUrl")

    retrieval_top_k: int = Field(default=4, alias="retrievalTopK")
    similarity_threshold: float = Field(default=0.03, alias="similarityThreshold")
    chunk_size: int = Field(default=512, alias="chunkSize")
    chunk_overlap: int = Field(default=50, alias="chunkOverlap")

    enable_web_search: bool = Field(default=True, alias="enableWebSearch")
    search_engine: str = Field(default="duckduckgo", alias="searchEngine")
    serp_api_key: Optional[str] = Field(default=None, alias="serpApiKey")

    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")


# ====== 文档相关 ======
class DocumentModel(BaseModel):
    id: str
    filename: str
    original_name: str
    file_type: FileType
    file_size: int
    upload_time: str
    status: DocumentStatus = DocumentStatus.PROCESSING
    chunk_count: int = 0
    error_message: Optional[str] = None


class UploadProgress(BaseModel):
    document_id: str
    stage: str  # uploading | parsing | chunking | embedding | complete | error
    progress: int  # 0-100
    message: str


# ====== 对话相关 ======
class SourceReference(BaseModel):
    document_id: str
    document_name: str
    content: str
    page_number: Optional[int] = None
    relevance_score: float


class SearchResultItem(BaseModel):
    title: str
    url: str
    snippet: str


class MessageModel(BaseModel):
    id: str
    role: MessageRole
    content: str
    timestamp: str
    sources: Optional[List[SourceReference]] = None
    search_results: Optional[List[SearchResultItem]] = None
    mode: Optional[AnswerMode] = AnswerMode.LOCAL


class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str
    use_web_search: Optional[bool] = None


class ConversationModel(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int = 0
    messages: List[MessageModel] = []


# ====== API响应包装 ======
class ApiResponse(BaseModel):
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str = datetime.now().isoformat()
