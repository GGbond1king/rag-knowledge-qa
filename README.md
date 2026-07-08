# RAG Knowledge QA

基于混合检索的 RAG 智能问答系统。支持多模型热切换、向量+BM25 双路召回 + RRF 融合排序、检索量化评估、网络搜索兜底。

## 核心亮点

- **双路检索 + RRF 融合排序** — 向量语义检索与 BM25 关键词检索通过 RRF 算法融合，实测 Recall 提升 11%
- **多厂商大模型热切换** — 支持阿里云百炼（GLM-5）、通义千问、DeepSeek、OpenAI、Ollama，前端可视化切换，无需重启
- **双层 Embedding 自动降级** — 优先调用 text-embedding-v3 API，异常时自动降级为本地 Python 哈希嵌入
- **网络搜索兜底** — 本地知识库无匹配时自动启用 DuckDuckGo 搜索，降低 LLM 幻觉
- **检索量化评估** — 内置 20 组测试用例 × 28 份含干扰文档，一键对比三种检索策略

## 技术栈

| 模块 | 选型 |
|------|------|
| 后端服务 | Python FastAPI + Uvicorn + Pydantic v2 |
| 前端框架 | React 18 + TypeScript + Vite + TailwindCSS |
| 向量检索 | InMemoryVectorStore（Pickle 持久化） |
| 关键词检索 | rank_bm25（BM25Okapi） |
| AI 模型 | OpenAI / DeepSeek / 阿里云百炼 / 通义千问 / Ollama |
| 网络搜索 | DuckDuckGo |

## 系统架构

```
用户提问
  ├── Embedding API → 向量语义检索 ──┐
  ├── 中文分词      → BM25 关键词检索 ──┤
  │                                   ├── RRF 融合排序
  │                                   │
  └── 有结果 → 拼接上下文 → LLM 流式输出
      ↓ 无结果
  DuckDuckGo 全网搜索 → LLM 流式输出
```

## 快速启动

```bash
# 1. 安装依赖
cd backend && pip install -r requirements.txt
cd .. && npm install

# 2. 环境配置
cp .env.example backend/.env
# 编辑 backend/.env，填入 API Key

# 3. 启动后端（终端1）
cd backend && python main.py
# → http://127.0.0.1:8000

# 4. 启动前端（终端2）
npm run dev
# → http://localhost:5173
```

使用流程：
1. 访问前端页面 → **系统配置** → 选择模型提供商、填写 API Key、保存
2. **知识库管理** → 上传 PDF / TXT / DOCX 文档
3. **智能问答** → 基于文档内容进行多轮对话

## 检索效果评估

项目内置对比评估脚本，自动对比三种检索策略：

```bash
cd backend && python evaluation/evaluate.py
```

输出示例：

| Query | 向量 | BM25 | RRF |
|-------|------|------|-----|
| NNLM与RNN梯度消失 | 0% | 100% | 100% |
| PyTorch比TensorFlow优势 | 0% | 100% | 100% |
| **平均 Recall@2** | **90%** | **100%** | **100%** |

RRF 双路融合相比纯向量检索召回率提升 **+11%**。

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Top-K | 4 | 单次检索返回文本片段数 |
| 相似度阈值 | 0.03 | 向量过滤阈值 |
| 分块大小 | 512 | 文档切片字符数 |
| 分块重叠 | 50 | 切片重叠字符数 |

## 项目结构

```
rag-knowledge-qa/
├── backend/
│   ├── api/            # API 路由（对话/配置/文档/健康检查）
│   ├── core/           # 核心逻辑（检索/嵌入/LLM/文档处理/搜索）
│   ├── models/         # 数据模型（Pydantic）
│   ├── evaluation/     # 检索效果评估脚本
│   └── data/           # 运行时数据（gitignore）
├── src/
│   ├── pages/          # 页面（智能问答/系统配置/知识库管理）
│   ├── components/     # 通用组件
│   ├── services/       # API 客户端
│   └── stores/         # 全局状态（zustand）
└── dist/               # 前端构建产物
```

## 后续规划

- **GraphRAG**：接入 Neo4j 实现知识图谱多跳推理（规划中）
- Rerank 重排模型接入，提升检索精度
- Docker 一键部署

## License

MIT
