# RAG Knowledge QA

基于混合检索的 RAG 智能问答系统。支持多模型热切换、向量+BM25+知识图谱三路混合检索、多层容错降级、检索量化评估。

核心检索、分块、嵌入、RRF 融合排序、图谱存储等逻辑均为自主编码实现，无重度第三方 RAG 框架封装。

## 核心亮点

- **三路混合检索 + RRF 融合排序** — 向量语义检索（理解近义词） + BM25 关键词检索（精确匹配） + 知识图谱关系检索（实体推理），通过 RRF 算法融合。实测 Recall@2 从纯向量的 90% 提升至 100%
- **多层容错降级机制**
  - **嵌入层降级**：优先调用云端 text-embedding-v3 API；接口不可用或无网络时自动切换为自研纯 Python 哈希嵌入，离线环境也能运行
  - **检索兜底降级**：三路检索均无有效结果时，自动启用 DuckDuckGo 全网搜索，搜索结果拼接为 LLM 上下文，从源头抑制幻觉编造
  - **模型接口降级**：单模型请求失败可提示切换其他提供商，前端可视化热切换，无需重启后端
- **GraphRAG 知识图谱检索** — 上传文档时自动抽取实体关系三元组构建知识图谱，问答时可回答跨文档的关系推理类问题
- **检索量化评估** — 内置 20 组测试查询 × 28 份文档（含干扰文档），一键输出三策略对比报表

## 技术栈

| 模块 | 选型 |
|------|------|
| 后端服务 | Python FastAPI + Uvicorn |
| 前端框架 | React 18 + TypeScript + Vite + TailwindCSS |
| 向量存储 | 自研 InMemoryVectorStore（纯 Python，手写余弦相似度，Pickle 持久化） |
| 关键词检索 | rank_bm25（BM25Okapi） |
| 知识图谱 | NetworkX MultiDiGraph（Pickle 持久化） |
| AI 模型 | 阿里云百炼 / OpenAI / DeepSeek / 通义千问 / Ollama |
| 网络搜索 | DuckDuckGo |
| 数据模型 | Pydantic v2 |

## 系统架构

```
用户提问
  ├── Embedding API → 向量语义检索 ──┐
  ├── 中文分词      → BM25 关键词检索 ──┤── RRF 融合排序
  ├── 实体抽取      → 图检索(BFS+子图) ──┘  (无实体则跳过)
  │                                          │
  └── 有结果 → 拼接上下文 → LLM 流式输出
      ↓ 三路均无匹配
  DuckDuckGo 全网搜索 → LLM 流式输出
```

RRF 融合策略：向量检索与 BM25 检索先通过 RRF（K=60）融合排序，图谱检索得到的实体关系上下文作为独立候选信息追加至结果列表，一并送入 LLM 生成回答。RRF 公式天然支持多路输入，不存在权重倾斜问题。

## 检索流程详解

### 文档处理（上传时）

1. **解析**：TXT 自动检测编码（UTF-8/GBK）；PDF 优先 pdfplumber 回退 PyPDF2；DOCX 使用 python-docx
2. **分块**：按段落优先切割，段落内再按字符截断（默认 512 字符，重叠 50），避免一句话被生硬拆断
3. **索引构建（三路并行）**：
   - Embedding API → 语义向量 → 存入向量库
   - 中文分词 → BM25 索引
   - LLM 抽取实体关系三元组 → NetworkX 知识图谱

### 问答时

1. 问题向量化 → 向量语义检索
2. 中文分词（单字+双字+英文词） → BM25 关键词检索
3. 实体抽取 → 模糊匹配图节点 → BFS 深度 2 子图提取（若无法抽取实体则跳过此路，不阻塞流程）
4. RRF 融合排序（K=60） → 拼接上下文 → LLM 流式生成

## 快速启动

```bash
# 1. 后端安装依赖
cd backend
pip install -r requirements.txt

# 2. 前端安装依赖
cd ..
npm install

# 3. 环境配置
cp .env.example backend/.env
# 编辑 backend/.env，填入 API Key

# 4. 启动后端（终端1）
cd backend && python main.py
# → http://127.0.0.1:8000

# 5. 启动前端（终端2）
npm run dev
# → http://localhost:5173
```

使用流程：
1. 访问前端页面 → **系统配置** → 选择模型提供商、填写 API Key、保存（参数修改实时生效，无需重启后端）
2. **知识库管理** → 上传 PDF / TXT / DOCX 文档
3. **智能问答** → 基于文档内容进行多轮对话

## 检索效果评估

项目内置自动评估脚本，覆盖 20 组测试查询 × 28 份含干扰文档：

```bash
cd backend && python evaluation/evaluate.py
```

输出示例：

| Query | 向量 | BM25 | RRF |
|-------|------|------|-----|
| NNLM与RNN梯度消失 | 0% | 100% | 100% |
| PyTorch比TensorFlow优势 | 0% | 100% | 100% |
| **平均 Recall@2** | **90%** | **100%** | **100%** |

- 评估指标：Recall@2（前 2 个检索结果中命中期望文档的比例）
- 干扰文档用于模拟真实场景，避免全量命中导致评估失效
- 输出自动生成三策略对比报表，支持直观对比

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Top-K | 4 | 单次检索返回文本片段数 |
| 相似度阈值 | 0.03 | 向量过滤阈值 |
| 分块大小 | 512 | 文档切片字符数（按段落优先切割） |
| 分块重叠 | 50 | 切片重叠字符数 |

## 项目说明

### 单实例单用户设计

当前版本为单用户单知识库架构，无多租户隔离。所有数据（文档、向量、图谱、对话历史）存储在 `backend/data/` 目录下，以 JSON / pickle 文件持久化。

删除文档时精准清除其对应的向量数据、BM25 索引条目及知识图谱实体节点，而非全库清空。

### 面试可解释性

本项目核心逻辑均自主编码实现，无重度第三方 RAG 框架封装：
- 向量存储：自研 InMemoryVectorStore，手写余弦相似度，非 ChromaDB / Pinecone 等现成方案
- 检索融合：手写 RRF 排序逻辑，非 LangChain 等框架
- GraphRAG：基于 NetworkX 自建图存储 + LLM 实体抽取，非 Neo4j / 微软 GraphRAG 一键脚本
- 文档分块：手写段落优先切割逻辑，非 LangChain TextSplitter

## 已修复的已知问题

| 问题 | 解决方案 |
|------|---------|
| 文档状态卡在"处理中" | 改为同步处理，处理完再返回响应 |
| 上传后字段显示 NaN | 前后端字段名对齐（统一 snake_case） |
| 服务重启后异步任务丢失 | 启动时自动清理残留的 processing 文档 |
| DeepSeek 无 Embedding API | 跳过 API 调用，直接使用本地嵌入 |
| 对话保存偶发 IndexError | 序列化前增加类型检查和兜底 |
| GraphRAG 查询延迟高 | 短查询跳过 LLM 抽取，直接规则提取 |
| ChromaDB Windows 段错误 | 使用自研纯 Python 向量存储替代 |
| 检索结果为空时列表索引越界 | 全局增加判空校验 |
| 配置参数修改需重启后端 | 前端参数修改实时热生效，无需重启 |

## 项目结构

```
rag-knowledge-qa/
├── backend/
│   ├── api/            # API 路由（对话/配置/文档/健康检查）
│   ├── core/
│   │   ├── retriever.py           # 向量存储 + BM25 + RRF 融合
│   │   ├── llm_manager.py         # 统一 LLM 调用（流式 + 嵌入）
│   │   ├── document_processor.py  # 文档解析 + 分块引擎
│   │   ├── embeddings.py          # 纯 Python 本地嵌入（降级兜底）
│   │   ├── web_search.py          # DuckDuckGo 搜索
│   │   ├── config.py              # 配置管理器
│   │   └── graphrag/              # 知识图谱模块
│   │       ├── graph_store.py     # 图存储（NetworkX + pickle）
│   │       ├── entity_extractor.py# LLM 实体关系抽取
│   │       └── graph_retriever.py # 图谱检索器
│   ├── models/schemas.py
│   ├── evaluation/evaluate.py     # 检索效果评估脚本
│   └── requirements.txt
├── src/                # 前端（React + TypeScript + TailwindCSS）
│   ├── pages/          # 智能问答 / 系统配置 / 知识库管理
│   ├── services/       # API 客户端
│   └── stores/         # 状态管理（zustand）
└── dist/               # 前端构建产物
```

## 后续规划

- **Docker Compose 容器化** — 一键部署后端 + 前端
- **Rerank 精排模型** — 在 RRF 融合后增加交叉重排，提升 Top-1 准确率
- **多租户 RBAC 权限系统** — 用户隔离、知识库权限管理
- **Milvus 分布式向量库适配** — 支持百万级向量规模

## License

MIT
