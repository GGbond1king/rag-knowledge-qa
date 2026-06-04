import axios from 'axios';
import type { ApiResponse, AppConfig, Document, Conversation } from '../types';

const API_BASE_URL = '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ====== 配置API ======

export const configApi = {
  async getConfig(): Promise<AppConfig> {
    const response = await apiClient.get<ApiResponse<AppConfig>>('/config');
    return response.data.data!;
  },

  async updateConfig(config: AppConfig): Promise<AppConfig> {
    const response = await apiClient.put<ApiResponse<AppConfig>>('/config', config);
    return response.data.data!;
  },
};

// ====== 文档API ======

export const documentsApi = {
  async uploadFile(file: File): Promise<Document> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post<ApiResponse<Document>>(
      '/documents/upload',
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data.data!;
  },

  async getDocuments(): Promise<Document[]> {
    const response = await apiClient.get<ApiResponse<Document[]>>('/documents');
    return response.data.data || [];
  },

  async deleteDocument(docId: string): Promise<void> {
    await apiClient.delete(`/documents/${docId}`);
  },

  async getStats(): Promise<any> {
    const response = await apiClient.get<ApiResponse<any>>('/documents/stats');
    return response.data.data;
  },
};

// ====== 对话API ======

export const chatApi = {
  async sendMessageStream(
    request: { conversationId?: string; message: string; useWebSearch?: boolean },
    onToken: (token: string) => void,
    onComplete: (conversationId: string) => void,
    onError: (error: string) => void
  ): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim();
            if (data === '[DONE]') {
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              if (parsed.error) {
                onError(parsed.error);
                return;
              }
              if (parsed.token) {
                onToken(parsed.token);
              }
              if (parsed.conversation_id) {
                onComplete(parsed.conversation_id);
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }
    } catch (error) {
      onError(error instanceof Error ? error.message : '请求失败');
    }
  },

  async getHistory(): Promise<Conversation[]> {
    const response = await apiClient.get<ApiResponse<Conversation[]>>('/chat/history');
    return response.data.data || [];
  },

  async getConversation(convId: string): Promise<Conversation> {
    const response = await apiClient.get<ApiResponse<Conversation>>(`/chat/history/${convId}`);
    return response.data.data!;
  },

  async deleteConversation(convId: string): Promise<void> {
    await apiClient.delete(`/chat/history/${convId}`);
  },

  async exportConversation(convId: string): Promise<Blob> {
    const response = await apiClient.post(
      `/chat/history/${convId}/export`,
      {},
      { responseType: 'blob' }
    );
    return response.data;
  },
};

// ====== 健康检查 ======

export const healthApi = {
  async check(): Promise<boolean> {
    try {
      const response = await apiClient.get('/health');
      return response.status === 200;
    } catch {
      return false;
    }
  },
};

export default apiClient;
