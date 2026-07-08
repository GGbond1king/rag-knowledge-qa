import { useState, useEffect, useRef } from 'react';
import { Save, CheckCircle, AlertCircle, Key, Cpu, Globe, SlidersHorizontal } from 'lucide-react';
import toast from 'react-hot-toast';
import type { AppConfig, ProviderType, ModelProvider } from '../types';
import { useAppStore } from '../stores/useAppStore';

// 提供商配置
const PROVIDERS: ModelProvider[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    apiKeyRequired: true,
    baseUrl: 'https://api.openai.com/v1',
    models: [
      { id: 'gpt-4o', name: 'GPT-4o', maxTokens: 128000 },
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini', maxTokens: 128000 },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', maxTokens: 128000 },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', maxTokens: 16385 },
    ],
  },
  {
    id: 'qwen',
    name: '通义千问',
    apiKeyRequired: true,
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: [
      { id: 'qwen-max', name: 'Qwen-Max', maxTokens: 32000 },
      { id: 'qwen-plus', name: 'Qwen-Plus', maxTokens: 131072 },
      { id: 'qwen-turbo', name: 'Qwen-Turbo', maxTokens: 131072 },
    ],
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    apiKeyRequired: true,
    baseUrl: 'https://api.deepseek.com/v1',
    models: [
      { id: 'deepseek-chat', name: 'DeepSeek Chat', maxTokens: 64000 },
      { id: 'deepseek-reasoner', name: 'DeepSeek Reasoner', maxTokens: 64000 },
      { id: 'deepseek-v4-flash', name: 'DeepSeek V4 Flash', maxTokens: 131072 },
      { id: 'deepseek-v3', name: 'DeepSeek V3', maxTokens: 64000 },
    ],
  },
  {
    id: 'bailian',
    name: '阿里云百炼',
    apiKeyRequired: true,
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: [
      { id: 'glm-5', name: 'GLM-5', maxTokens: 131072 },
      { id: 'glm-4', name: 'GLM-4', maxTokens: 131072 },
      { id: 'qwen-max', name: 'Qwen-Max', maxTokens: 32000 },
      { id: 'qwen-plus', name: 'Qwen-Plus', maxTokens: 131072 },
      { id: 'qwen-turbo', name: 'Qwen-Turbo', maxTokens: 131072 },
    ],
  },
  {
    id: 'ollama',
    name: 'Ollama 本地',
    apiKeyRequired: false,
    baseUrl: 'http://localhost:11434/v1',
    models: [],
  },
];

const ConfigPage: React.FC = () => {
  const { config, loadConfig, updateConfig, configLoading } = useAppStore();
  
  // 表单状态
  const [form, setForm] = useState<AppConfig>({
    provider: 'deepseek',
    apiKey: '',
    model: 'deepseek-chat',
    embeddingModel: 'all-MiniLM-L6-v2',
    customBaseUrl: '',
    retrievalTopK: 4,
    similarityThreshold: 0.03,
    chunkSize: 512,
    chunkOverlap: 50,
    enableWebSearch: true,
    searchEngine: 'duckduckgo',
    serpApiKey: '',
  });
  
  const [showApiKey, setShowApiKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const isSavingRef = useRef(false);

  useEffect(() => {
    loadConfig();
  }, []);

  useEffect(() => {
    if (config && !isSavingRef.current) {
      setForm({
        provider: config.provider || 'deepseek',
        apiKey: config.apiKey || '',
        model: config.model || 'deepseek-chat',
        embeddingModel: config.embeddingModel || 'all-MiniLM-L6-v2',
        customBaseUrl: config.customBaseUrl || '',
        retrievalTopK: config.retrievalTopK ?? 4,
        similarityThreshold: config.similarityThreshold ?? 0.03,
        chunkSize: config.chunkSize ?? 512,
        chunkOverlap: config.chunkOverlap ?? 50,
        enableWebSearch: config.enableWebSearch ?? true,
        searchEngine: (config.searchEngine as any) || 'duckduckgo',
        serpApiKey: config.serpApiKey || '',
      });
    }
  }, [config]);

  const currentProvider = PROVIDERS.find(p => p.id === form.provider);

  const handleSave = async () => {
    setSaving(true);
    isSavingRef.current = true;
    try {
      await updateConfig(form);
      // 延迟重置 saving 标记，避免与 config 更新触发的 useEffect 竞争
      setTimeout(() => { isSavingRef.current = false; }, 100);
      toast.success('配置保存成功');
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      isSavingRef.current = false;
      toast.error('保存失败，请检查输入');
    } finally {
      setSaving(false);
    }
  };

  if (configLoading && !config) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-2">系统配置</h1>
        <p className="text-slate-400 text-sm">配置AI模型、API密钥和检索参数</p>
      </div>

      {/* 主要配置卡片 */}
      <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-2xl p-6 space-y-6">
        {/* 模型提供商选择 */}
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <Cpu className="w-4 h-4 text-cyan-400" />
            模型提供商
          </label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {PROVIDERS.map((provider) => (
              <button
                key={provider.id}
                onClick={() => setForm({ ...form, provider: provider.id as ProviderType, model: provider.models[0]?.id || '' })}
                className={`
                  relative p-4 rounded-xl border transition-all duration-200 text-left
                  ${form.provider === provider.id
                    ? 'border-cyan-500/50 bg-cyan-500/10 shadow-lg shadow-cyan-500/10'
                    : 'border-slate-700 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800'
                  }
                `}
              >
                <div className="font-semibold text-sm text-white mb-1">{provider.name}</div>
                <div className="text-xs text-slate-400">
                  {provider.apiKeyRequired ? '需要API Key' : '本地运行'}
                </div>
                {form.provider === provider.id && (
                  <CheckCircle className="absolute top-3 right-3 w-4 h-4 text-cyan-400" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* API Key */}
        {currentProvider?.apiKeyRequired && (
          <div className="space-y-3">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
              <Key className="w-4 h-4 text-cyan-400" />
              API 密钥
            </label>
            <div className="relative">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={form.apiKey}
                onChange={(e) => setForm({ ...form, apiKey: e.target.value })}
                placeholder={`输入${currentProvider.name}的API密钥`}
                className="w-full px-4 py-3 pr-12 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500/50 transition-all"
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white"
              >
                {showApiKey ? '隐藏' : '显示'}
              </button>
            </div>
          </div>
        )}

        {/* 模型选择 */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-slate-300">对话模型</label>
          <select
            value={form.model}
            onChange={(e) => setForm({ ...form, model: e.target.value })}
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-cyan-500 transition-all appearance-none cursor-pointer"
          >
            {currentProvider?.models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.name} (最大{model.maxTokens.toLocaleString()} tokens)
              </option>
            ))}
            {(!currentProvider?.models || currentProvider.models.length === 0) && (
              <option value="">请确保Ollama服务正在运行</option>
            )}
          </select>
        </div>

        {/* 自定义API地址 */}
        <div className="space-y-3">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-300">
            <Globe className="w-4 h-4 text-cyan-400" />
            自定义API地址（可选）
          </label>
          <input
            type="text"
            value={form.customBaseUrl || ''}
            onChange={(e) => setForm({ ...form, customBaseUrl: e.target.value })}
            placeholder={`默认: ${currentProvider?.baseUrl || ''}`}
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-all"
          />
          <p className="text-xs text-slate-500">如使用代理或兼容API服务，可填写自定义地址</p>
        </div>

        {/* Embedding模型选择 */}
        <div className="space-y-3">
          <label className="text-sm font-medium text-slate-300">Embedding模型（向量嵌入）</label>
          <select
            value={form.embeddingModel}
            onChange={(e) => setForm({ ...form, embeddingModel: e.target.value })}
            className="w-full px-4 py-3 bg-slate-800 border border-slate-700 rounded-xl text-white focus:outline-none focus:border-cyan-500 transition-all appearance-none cursor-pointer"
          >
            <option value="text-embedding-v3">text-embedding-v3 (阿里云百炼，1024维)</option>
            <option value="all-MiniLM-L6-v2">all-MiniLM-L6-v2 (通用英文，384维)</option>
            <option value="multilingual-e5-large">multilingual-e5-large (中英双语，1024维)</option>
            <option value="bge-large-zh-v1.5">bge-large-zh-v1.5 (中文优化，1024维)</option>
          </select>
        </div>

        {/* 高级设置折叠面板 */}
        <div>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <SlidersHorizontal className="w-4 h-4" />
            高级设置
            <span className={`transform transition-transform ${showAdvanced ? 'rotate-180' : ''}`}>▼</span>
          </button>
          
          {showAdvanced && (
            <div className="mt-4 space-y-4 pt-4 border-t border-slate-800">
              {/* Top-K */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">检索返回数量 (Top-K)</label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={form.retrievalTopK}
                    onChange={(e) => setForm({ ...form, retrievalTopK: parseInt(e.target.value) || 4 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-cyan-500"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">相似度阈值</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={form.similarityThreshold}
                    onChange={(e) => setForm({ ...form, similarityThreshold: parseFloat(e.target.value) || 0.03 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-cyan-500"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">文本分块大小</label>
                  <input
                    type="number"
                    min="100"
                    max="2048"
                    value={form.chunkSize}
                    onChange={(e) => setForm({ ...form, chunkSize: parseInt(e.target.value) || 512 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-cyan-500"
                  />
                </div>
                
                <div className="space-y-2">
                  <label className="text-xs text-slate-400">分块重叠大小</label>
                  <input
                    type="number"
                    min="0"
                    max="200"
                    value={form.chunkOverlap}
                    onChange={(e) => setForm({ ...form, chunkOverlap: parseInt(e.target.value) || 50 })}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 保存按钮 */}
        <div className="flex justify-end pt-4 border-t border-slate-800">
          <button
            onClick={handleSave}
            disabled={saving}
            className={`
              flex items-center gap-2 px-6 py-3 rounded-xl font-medium text-sm transition-all duration-200
              ${saved
                ? 'bg-emerald-500 text-white'
                : saving
                  ? 'bg-cyan-500/70 text-white cursor-wait'
                  : 'bg-gradient-to-r from-cyan-500 to-emerald-500 text-white hover:shadow-lg hover:shadow-cyan-500/25 active:scale-[0.98]'
              }
            `}
          >
            {saved ? (
              <>
                <CheckCircle className="w-4 h-4" />
                已保存
              </>
            ) : saving ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                保存配置
              </>
            )}
          </button>
        </div>
      </div>

      {/* 使用提示 */}
      <div className="bg-blue-500/10 border border-blue-500/20 rounded-2xl p-5">
        <div className="flex gap-3">
          <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-200/80 space-y-1">
            <p className="font-medium text-blue-300">使用提示</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>首次使用请先配置AI模型和API密钥</li>
              <li>推荐使用DeepSeek作为入门模型，性价比较高</li>
              <li>Embedding模型建议根据文档语言选择合适的版本</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfigPage;
