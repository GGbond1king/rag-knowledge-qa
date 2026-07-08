# Rag Knowledge QA

基于 RAG（检索增强生成）的智能文档知识库问答系统。支持多模型热切换、向量+关键词双路混合检索、知识库管理和多轮对话。

## 核心亮点

- **双路混合检索** — 向量语义检索 + BM25 关键词检索，通过 RRF 算法融合排序
- **多模型热切换** — 支持 OpenAI、DeepSeek、阿里云百炼（GLM-5）、通义千问、Ollama 本地模型
- **API 嵌入优先** — 自动使用 text-embedding-v3 等工业级语义嵌入模型，纯 Python 哈希嵌入作为离线兜底
- **可评估体系** — 内置 20 组测试用例，一键跑出召回率对比报告
- **自动降级** — 本地知识库无结果时自动切换网络搜索（DuckDuckGo）

## 技术栈

| 层 | 技术 |
|------|------|
| **后端** | Python FastAPI + Uvicorn |
| **前端** | React 18 + TypeScript + Vite + TailwindCSS |
| **向量存储** | 纯 Python InMemoryVectorStore（pickle 持久化） |
| **关键词检索** | rank_bm25（BM25Okapi） |
| **AI 模型** | OpenAI / DeepSeek / 阿里云百炼 / 通义千问 / Ollama |
| **网络搜索** | DuckDuckGo |
| **数据模型** | Pydantic v2 |

## 架构

```
用户输入 → Embedding API → 向量检索 ──┐
                                        ├── RRF 融合 → LLM → 流式输出
用户输入 → BM25 分词  → 关键词检索 ──┘
                          ↓ 无结果
                      DuckDuckGo 搜索
```

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend && pip install -r requirements.txt

# 前端
cd .. && npm install
```

### 2. 配置

复制环境变量文件并填入 API Key：

```bash
cp .env.example backend/.env
```

编辑 `backend/.env`：

```env
# 阿里云百炼（推荐）
BAILIAN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 或 DeepSeek
# DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 启动

```bash
# 终端1 - 后端 (默认 http://127.0.0.1:8000)
cd backend && python main.py

# 终端2 - 前端 (默认 http://localhost:5173)
npm run dev
```

### 4. 使用

1. 打开浏览器访问 `http://localhost:5173`
2. 进入 **系统配置**，选择模型提供商（如阿里云百炼），填入 API Key，选择模型（如 glm-5），保存
3. 进入 **知识库管理**，上传 PDF/DOCX/TXT 文档
4. 进入 **智能问答**，基于文档内容提问

## 检索效果评估

内置 20 组测试查询 × 28 份文档（含干扰文档）的评估脚本：

```bash
cd backend && python evaluation/evaluate.py
```

输出示例：

```
  Query                             向量    BM25     RRF
  NNLM与RNN梯度消失                   0%    100%    100%
  PyTorch比TensorFlow优势             0%    100%    100%
  ─────────────────────────────────────────────────
  平均 Recall@2                     90%    100%    100%

  RRF 优于纯向量: +11%
```

## 配置项

### AI 模型提供商

| 提供商 | 说明 | 默认模型 |
|--------|------|---------|
| 阿里云百炼 | 推荐，支持 GLM-5 和 text-embedding-v3 | glm-5 |
| OpenAI | GPT 系列 | gpt-4o |
| DeepSeek | 性价比高 | deepseek-chat |
| 通义千问 | 阿里系 | qwen-max |
| Ollama | 本地部署 | 动态获取 |

### 检索参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Top-K | 4 | 检索返回的文档片段数 |
| 相似度阈值 | 0.03 | 向量相似度过滤阈值 |
| 分块大小 | 512 | 文档切分粒度（字符） |
| 分块重叠 | 50 | 相邻分块重叠字符数 |

## 项目结构

```
rag-knowledge-qa/
├── backend/
│   ├── api/            # API 路由（对话/配置/文档/健康检查）
│   ├── core/           # 核心逻辑（检索/嵌入/LLM/文档处理/网络搜索）
│   ├── models/         # Pydantic 数据模型
│   ├── evaluation/     # 检索效果评估脚本
│   └── data/           # 运行时数据（已 gitignore）
├── src/
│   ├── pages/          # 页面组件（对话/配置/知识库）
│   ├── components/     # 布局组件
│   ├── services/       # API 客户端（axios）
│   └── stores/         # 状态管理（zustand）
└── dist/               # 前端构建产物
```

## License

MIT