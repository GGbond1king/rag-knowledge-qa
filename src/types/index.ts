// ====== 枚举类型 ======

export type ProviderType = 'openai' | 'qwen' | 'deepseek' | 'ollama';
export type FileType = 'txt' | 'pdf' | 'docx';
export type DocumentStatus = 'processing' | 'indexed' | 'failed';
export type MessageRole = 'user' | 'assistant';
export type AnswerMode = 'local' | 'web' | 'hybrid';

// ====== 配置相关 ======

export interface ModelOption {
  id: string;
  name: string;
  maxTokens: number;
}

export interface ModelProvider {
  id: ProviderType;
  name: string;
  apiKeyRequired: boolean;
  baseUrl?: string;
  models: ModelOption[];
}

export interface AppConfig {
  provider: ProviderType;
  apiKey: string;
  model: string;
  embeddingModel: string;
  customBaseUrl?: string;

  // 检索参数
  retrievalTopK: number;
  similarityThreshold: number;
  chunkSize: number;
  chunkOverlap: number;

  // 网络搜索
  enableWebSearch: boolean;
  searchEngine: 'duckduckgo' | 'serpapi';
  serpApiKey?: string;

  createdAt?: string;
  updatedAt?: string;
}

// ====== 文档相关 ======

export interface Document {
  id: string;
  filename: string;
  originalName: string;
  fileType: FileType;
  fileSize: number;
  uploadTime: string;
  status: DocumentStatus;
  chunkCount: number;
  errorMessage?: string;
}

export interface UploadProgress {
  documentId: string;
  stage: 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'complete' | 'error';
  progress: number;
  message: string;
}

// ====== 对话相关 ======

export interface SourceReference {
  documentId: string;
  documentName: string;
  content: string;
  pageNumber?: number;
  relevanceScore: number;
}

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  sources?: SourceReference[];
  searchResults?: SearchResult[];
  mode?: AnswerMode;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  messages?: Message[];
}

export interface ChatRequest {
  conversationId?: string;
  message: string;
  useWebSearch?: boolean;
}

// ====== API响应包装 ======

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}
