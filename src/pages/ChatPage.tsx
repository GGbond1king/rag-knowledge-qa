import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Send,
  Plus,
  MessageSquare,
  Trash2,
  Download,
  BookOpen,
  Globe,
  Bot,
  User,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Sparkles,
  Loader2,
  Pencil,
  Check,
  X
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import toast from 'react-hot-toast';
import type { Conversation, Message, SourceReference, SearchResult, AnswerMode } from '../types';
import { useAppStore } from '../stores/useAppStore';
import { chatApi } from '../services/api';

const ChatPage: React.FC = () => {
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const {
    conversations,
    currentConversation,
    currentMessages,
    isLoading,
    loadConversations,
    selectConversation,
    deleteConversation,
    renameConversation,
    addMessage,
    clearCurrentConversation,
    setLoading,
  } = useAppStore();

  const [inputValue, setInputValue] = useState('');
  const [showSidebar, setShowSidebar] = useState(true);
  const [expandedSources, setExpandedSources] = useState<string | null>(null);
  const [renamingConv, setRenamingConv] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  useEffect(() => {
    loadConversations();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async () => {
    const message = inputValue.trim();
    if (!message || isLoading) return;

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    addMessage(userMessage);
    setInputValue('');
    setLoading(true);

    // 创建助手消息占位
    let assistantContent = '';
    let sources: SourceReference[] = [];
    let searchResults: SearchResult[] = [];
    let mode: AnswerMode = 'local';

    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      sources: [],
      searchResults: [],
      mode: 'local',
    };
    addMessage(assistantMessage);

    try {
      await chatApi.sendMessageStream(
        {
          conversationId: currentConversation?.id,
          message: message,
        },
        (token) => {
          assistantContent += token;
          // 更新最后一条消息内容
          addMessage({
            ...assistantMessage,
            id: assistantMessage.id,
            content: assistantContent,
          });
        },
        (conversationId) => {
          // 对话创建完成
          if (!currentConversation?.id && conversationId) {
            loadConversations();
          }
        },
        (error) => {
          toast.error(error);
          addMessage({
            ...assistantMessage,
            id: assistantMessage.id,
            content: assistantContent || `错误: ${error}`,
          });
        }
      );

      // 完成后更新消息
      addMessage({
        ...assistantMessage,
        id: assistantMessage.id,
        content: assistantContent,
        sources,
        searchResults,
        mode,
      });
    } catch (error) {
      console.error('发送消息出错:', error);
      toast.error('请求失败');
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleNewChat = () => {
    clearCurrentConversation();
    setInputValue('');
  };

  const handleSelectConversation = async (conv: Conversation) => {
    try {
      const detail = await chatApi.getConversation(conv.id);
      selectConversation({ ...conv, messages: detail.messages });
    } catch (error) {
      selectConversation(conv);
    }
  };

  const handleDeleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('确定要删除这个对话吗？')) return;
    
    try {
      await deleteConversation(convId);
      toast.success('对话已删除');
    } catch (error) {
      toast.error('删除失败');
    }
  };

  const handleStartRename = (convId: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setRenamingConv(convId);
    setRenameValue(currentTitle);
    // 输入框自动聚焦（通过 setTimeout 确保 input 已渲染）
    setTimeout(() => {
      const input = document.getElementById(`rename-input-${convId}`) as HTMLInputElement;
      input?.focus();
      input?.select();
    }, 50);
  };

  const handleConfirmRename = async (convId: string) => {
    const title = renameValue.trim();
    if (!title) return;
    try {
      await renameConversation(convId, title);
      setRenamingConv(null);
      toast.success('重命名成功');
    } catch {
      toast.error('重命名失败');
    }
  };

  const handleCancelRename = () => {
    setRenamingConv(null);
    setRenameValue('');
  };

  const handleExport = async (convId: string, title: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const blob = await chatApi.exportConversation(convId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title}.md`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('导出成功');
    } catch (error) {
      toast.error('导出失败');
    }
  };

  const getModeBadge = (mode?: AnswerMode) => {
    switch (mode) {
      case 'local':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400">
            <BookOpen className="w-3 h-3" />
            本地知识库
          </span>
        );
      case 'web':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/15 text-blue-400">
            <Globe className="w-3 h-3" />
            网络搜索
          </span>
        );
      case 'hybrid':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-violet-500/15 text-violet-400">
            <Sparkles className="w-3 h-3" />
            混合模式
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="h-[calc(100vh-5rem)] flex -m-4 md:-m-6 lg:-m-8">
      {/* 对话历史侧边栏 */}
      <aside
        className={`
          w-72 border-r border-slate-800 bg-slate-900/50 flex flex-col
          transition-transform duration-300 ${showSidebar ? 'translate-x-0' : '-translate-x-full'} 
          absolute lg:relative z-20 h-full
        `}
      >
        <div className="p-4 border-b border-slate-800">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-emerald-500 rounded-xl text-white font-medium text-sm hover:shadow-lg hover:shadow-cyan-500/25 transition-all active:scale-[0.98]"
          >
            <Plus className="w-4 h-4" />
            新建对话
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {conversations.map((conv) => (
            <button
              key={conv.id}
              onClick={() => renamingConv === conv.id ? null : handleSelectConversation(conv)}
              className={`
                w-full group flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left transition-all
                ${currentConversation?.id === conv.id
                  ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-white border border-transparent'
                }
              `}
            >
              <MessageSquare className="w-4 h-4 flex-shrink-0" />

              {renamingConv === conv.id ? (
                <div className="flex-1 flex items-center gap-1">
                  <input
                    id={`rename-input-${conv.id}`}
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={(e) => {
                      e.stopPropagation();
                      if (e.key === 'Enter') handleConfirmRename(conv.id);
                      if (e.key === 'Escape') handleCancelRename();
                    }}
                    className="flex-1 min-w-0 px-2 py-1 text-sm bg-slate-700 border border-cyan-500 rounded text-white outline-none"
                    onClick={(e) => e.stopPropagation()}
                  />
                  <span onClick={(e) => { e.stopPropagation(); handleConfirmRename(conv.id); }} className="p-1 hover:text-emerald-400 cursor-pointer">
                    <Check className="w-3.5 h-3.5" />
                  </span>
                  <span onClick={(e) => { e.stopPropagation(); handleCancelRename(); }} className="p-1 hover:text-red-400 cursor-pointer">
                    <X className="w-3.5 h-3.5" />
                  </span>
                </div>
              ) : (
                <span className="flex-1 truncate text-sm">{conv.title}</span>
              )}

              {renamingConv !== conv.id && (
              <div className="hidden group-hover:flex items-center gap-1 opacity-70">
                <span
                  onClick={(e) => handleStartRename(conv.id, conv.title, e)}
                  className="p-1 hover:text-cyan-400 cursor-pointer"
                  title="重命名"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </span>
                <span
                  onClick={(e) => handleExport(conv.id, conv.title, e)}
                  className="p-1 hover:text-cyan-400 cursor-pointer"
                  title="导出"
                >
                  <Download className="w-3.5 h-3.5" />
                </span>
                <span
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                  className="p-1 hover:text-red-400 cursor-pointer"
                  title="删除"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </span>
              </div>
              )}
            </button>
          ))}

          {conversations.length === 0 && (
            <div className="text-center py-8 text-slate-500 text-sm">
              暂无对话记录
            </div>
          )}
        </div>
      </aside>

      {/* 主对话区域 */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* 对话头部 */}
        <header className="px-6 py-3 border-b border-slate-800 flex items-center justify-between bg-slate-950/80 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="lg:hidden p-2 rounded-lg hover:bg-slate-800 text-slate-400"
            >
              {showSidebar ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
            </button>
            
            <div>
              <h2 className="font-semibold text-white text-sm">
                {currentConversation?.title || '新对话'}
              </h2>
              {currentMessages.length > 0 && (
                <p className="text-xs text-slate-500">{currentMessages.length} 条消息</p>
              )}
            </div>
          </div>

          {getModeBadge(currentMessages[currentMessages.length - 1]?.mode)}
        </header>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto space-y-6 p-6">
          {currentMessages.length === 0 ? (
            /* 空状态 */
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-cyan-500/20 to-emerald-500/20 flex items-center justify-center mb-6">
                <Bot className="w-10 h-10 text-cyan-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">开始智能问答</h3>
              <p className="text-slate-400 text-sm max-w-md">
                基于你上传的文档进行提问，如果本地知识库无法回答，系统会自动搜索网络获取信息。
              </p>
              
              <div className="grid grid-cols-2 gap-3 mt-8 w-full max-w-lg">
                {[
                  { icon: BookOpen, label: '基于文档', desc: '从知识库中检索答案' },
                  { icon: Globe, label: '网络搜索', desc: '自动搜索补充信息' },
                ].map((item) => (
                  <div key={item.label} className="p-4 bg-slate-900/50 rounded-xl border border-slate-800">
                    <item.icon className="w-5 h-5 text-cyan-400 mb-2" />
                    <p className="text-sm font-medium text-white">{item.label}</p>
                    <p className="text-xs text-slate-500 mt-1">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* 消息列表 */
            currentMessages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                )}

                <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                  {/* 消息气泡 */}
                  <div
                    className={`
                      rounded-2xl px-5 py-3.5
                      ${msg.role === 'user'
                        ? 'bg-gradient-to-r from-cyan-500 to-cyan-600 text-white rounded-tr-md'
                        : 'bg-slate-800/80 text-slate-100 border border-slate-700/50 rounded-tl-md'
                      }
                    `}
                  >
                    {msg.role === 'assistant' ? (
                      <div className="prose prose-invert prose-sm max-w-none prose-headings:text-white prose-p:text-slate-200 prose-code:text-cyan-300 prose-pre:bg-slate-900 prose-pre:border-slate-700">
                        <ReactMarkdown
                          components={{
                            code({ node, inline, className, children, ...props }: any) {
                              const match = /language-(\w+)/.exec(className || '');
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={oneDark as { [key: string]: React.CSSProperties }}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={`${className} px-1.5 py-0.5 rounded bg-slate-700 text-cyan-300 text-sm`} {...props}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {msg.content || (isLoading && msg.id === currentMessages[currentMessages.length - 1]?.id ? '思考中...' : '')}
                        </ReactMarkdown>
                        {isLoading && msg.id === currentMessages[currentMessages.length - 1]?.id && !msg.content && (
                          <div className="flex items-center gap-2 text-slate-400">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            <span>正在生成回答...</span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                    )}
                  </div>

                  {/* 来源引用 */}
                  {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3 ml-2">
                      <button
                        onClick={() => setExpandedSources(expandedSources === msg.id ? null : msg.id)}
                        className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-cyan-400 transition-colors"
                      >
                        <BookOpen className="w-3.5 h-3.5" />
                        引用来源 ({msg.sources.length})
                        {expandedSources === msg.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                      </button>
                      
                      {expandedSources === msg.id && (
                        <div className="mt-2 space-y-2 p-3 bg-slate-900/80 rounded-xl border border-slate-800">
                          {msg.sources.map((source, idx) => (
                            <div key={idx} className="text-xs space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-cyan-400">{source.documentName}</span>
                                <span className="text-slate-500">相关度: {(source.relevanceScore * 100).toFixed(0)}%</span>
                              </div>
                              <p className="text-slate-400 line-clamp-3">{source.content}</p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 网络搜索结果 */}
                  {msg.role === 'assistant' && msg.searchResults && msg.searchResults.length > 0 && (
                    <div className="mt-3 ml-2">
                      <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-2">
                        <Globe className="w-3.5 h-3.5" />
                        参考链接 ({msg.searchResults.length})
                      </div>
                      
                      <div className="space-y-1.5">
                        {msg.searchResults.map((result, idx) => (
                          <a
                            key={idx}
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-start gap-2 p-2 bg-slate-900/80 rounded-lg border border-slate-800 hover:border-slate-700 transition-colors group"
                          >
                            <ExternalLink className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0 group-hover:text-cyan-400" />
                            <div className="min-w-0">
                              <p className="text-xs font-medium text-cyan-400 truncate group-hover:text-cyan-300">
                                {result.title}
                              </p>
                              <p className="text-xs text-slate-500 line-clamp-1 mt-0.5">{result.snippet}</p>
                            </div>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center order-1">
                    <User className="w-4 h-4 text-slate-300" />
                  </div>
                )}
              </div>
            ))
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入区域 */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/90 backdrop-blur-sm">
          <div className="max-w-4xl mx-auto">
            <div className="relative flex items-end gap-3 bg-slate-800/80 rounded-2xl border border-slate-700 focus-within:border-cyan-500/50 focus-within:ring-1 focus-within:ring-cyan-500/20 transition-all">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入你的问题..."
                rows={1}
                className="flex-1 resize-none bg-transparent px-5 py-3.5 text-white placeholder-slate-500 focus:outline-none max-h-32 text-sm"
                style={{ minHeight: '48px' }}
              />
              
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim() || isLoading}
                className={`
                  m-2 p-2.5 rounded-xl transition-all duration-200 flex-shrink-0
                  ${inputValue.trim() && !isLoading
                    ? 'bg-gradient-to-r from-cyan-500 to-emerald-500 text-white hover:shadow-lg hover:shadow-cyan-500/25 active:scale-95'
                    : 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  }
                `}
              >
                {isLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <Send className="w-5 h-5" />
                )}
              </button>
            </div>
            
            <p className="text-center text-xs text-slate-600 mt-2">
              按 Enter 发送，Shift+Enter 换行 · 基于RAG技术提供智能问答服务
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ChatPage;
