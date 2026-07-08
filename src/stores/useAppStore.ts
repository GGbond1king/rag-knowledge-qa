import { create } from 'zustand';
import type { AppConfig, Document, Conversation, Message } from '../types';
import { configApi, documentsApi, chatApi } from '../services/api';

interface AppState {
  // 配置状态
  config: AppConfig | null;
  configLoading: boolean;
  
  // 文档状态
  documents: Document[];
  documentsLoading: boolean;
  stats: any;
  
  // 对话状态
  conversations: Conversation[];
  currentConversation: Conversation | null;
  currentMessages: Message[];
  isLoading: boolean;
  
  // Actions - Config
  loadConfig: () => Promise<void>;
  updateConfig: (config: AppConfig) => Promise<void>;
  
  // Actions - Documents
  loadDocuments: () => Promise<void>;
  uploadFile: (file: File) => Promise<void>;
  deleteDocument: (docId: string) => Promise<void>;
  loadStats: () => Promise<void>;
  
  // Actions - Conversations
  loadConversations: () => Promise<void>;
  selectConversation: (conv: Conversation | null) => void;
  deleteConversation: (convId: string) => Promise<void>;
  renameConversation: (convId: string, title: string) => Promise<void>;
  addMessage: (message: Message) => void;
  clearCurrentConversation: () => void;
  setLoading: (loading: boolean) => void;
}

export const useAppStore = create<AppState>((set, get) => ({
  // 初始状态
  config: null,
  configLoading: false,
  documents: [],
  documentsLoading: false,
  stats: {},
  conversations: [],
  currentConversation: null,
  currentMessages: [],
  isLoading: false,

  // Config Actions
  loadConfig: async () => {
    set({ configLoading: true });
    try {
      const config = await configApi.getConfig();
      set({ config, configLoading: false });
    } catch (error) {
      console.error('加载配置失败:', error);
      set({ configLoading: false });
    }
  },

  updateConfig: async (config) => {
    try {
      const updated = await configApi.updateConfig(config);
      set({ config: updated });
    } catch (error) {
      console.error('更新配置失败:', error);
      throw error;
    }
  },

  // Documents Actions
  loadDocuments: async () => {
    set({ documentsLoading: true });
    try {
      const docs = await documentsApi.getDocuments();
      set({ documents: docs, documentsLoading: false });
    } catch (error) {
      console.error('加载文档列表失败:', error);
      set({ documentsLoading: false });
    }
  },

  uploadFile: async (file) => {
    try {
      await documentsApi.uploadFile(file);
      // 上传成功后刷新列表
      get().loadDocuments();
      get().loadStats();
    } catch (error) {
      console.error('上传文件失败:', error);
      throw error;
    }
  },

  deleteDocument: async (docId) => {
    try {
      await documentsApi.deleteDocument(docId);
      get().loadDocuments();
      get().loadStats();
    } catch (error) {
      console.error('删除文档失败:', error);
      throw error;
    }
  },

  loadStats: async () => {
    try {
      const stats = await documentsApi.getStats();
      set({ stats });
    } catch (error) {
      console.error('加载统计信息失败:', error);
    }
  },

  // Conversations Actions
  loadConversations: async () => {
    try {
      const convs = await chatApi.getHistory();
      set({ conversations: convs });
    } catch (error) {
      console.error('加载对话历史失败:', error);
    }
  },

  selectConversation: (conv) => {
    if (conv) {
      set({ 
        currentConversation: conv, 
        currentMessages: conv.messages || [] 
      });
    } else {
      set({ currentConversation: null, currentMessages: [] });
    }
  },

  renameConversation: async (convId, title) => {
    try {
      await chatApi.renameConversation(convId, title);
      get().loadConversations();
      const state = get();
      if (state.currentConversation?.id === convId) {
        set({ currentConversation: { ...state.currentConversation, title } });
      }
    } catch (error) {
      console.error('重命名对话失败:', error);
      throw error;
    }
  },

  deleteConversation: async (convId) => {
    try {
      await chatApi.deleteConversation(convId);
      const state = get();
      if (state.currentConversation?.id === convId) {
        set({ currentConversation: null, currentMessages: [] });
      }
      get().loadConversations();
    } catch (error) {
      console.error('删除对话失败:', error);
      throw error;
    }
  },

  addMessage: (message) => {
    set((state) => {
      const exists = state.currentMessages.find(m => m.id === message.id);
      if (exists) {
        // 更新已有消息（用于流式输出时追加内容）
        return {
          currentMessages: state.currentMessages.map(m =>
            m.id === message.id ? { ...m, ...message } : m
          ),
        };
      }
      // 新消息
      return { currentMessages: [...state.currentMessages, message] };
    });
  },

  clearCurrentConversation: () => {
    set({ currentConversation: null, currentMessages: [] });
  },

  setLoading: (loading) => {
    set({ isLoading: loading });
  },
}));
