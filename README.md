RAG Knowledge QA | 工业级混合检索知识库问答系统
⭐ 基于混合检索 RAG 的前后端分离智能问答系统｜支持多模型热切换、RRF 融合排序、检索量化评估、全自动降级兜底
可无缝迭代升级为 GraphRAG 知识图谱多跳推理架构

---
📌 项目简介
传统单向量 RAG 普遍存在 关键词漏召回、语义漂移、问答不稳定、幻觉严重 等问题。
本项目基于 FastAPI + React 搭建全栈轻量化工业级 RAG 系统，摒弃单一向量检索，采用 向量语义检索 + BM25 关键词检索双路召回 + RRF 融合排序 核心方案，大幅提升文档问答准确率。
项目支持多厂商大模型热切换、双层嵌入降级、全网搜索兜底、完整量化评估体系，是一套可部署、可评测、可二次开发、可进阶 GraphRAG 的标准 AI 应用工程项目。

---
✨ 核心项目亮点
- 🔥 双路检索 + RRF 融合排序（核心技术亮点）
同时保留「向量语义理解」和「BM25 关键词精准匹配」优势，通过 RRF 算法自动融合权重，解决单一检索缺陷。
实测对比纯向量检索整体召回率提升 11%。
- 🤖 多厂商大模型热切换
原生支持：阿里云百炼 GLM-5、通义千问、DeepSeek、OpenAI、Ollama 本地模型。
前端可视化切换模型，无需重启后端服务，支持云端/本地离线双部署。
- ⚙️ 双层 Embedding 自动降级
优先调用工业级 text-embedding-v3 嵌入接口；
接口异常/无网络时自动降级为本地 Python 哈希嵌入，保证系统全天候可用。
- 🌐 智能全网搜索兜底
本地知识库检索无结果时，自动启用 DuckDuckGo 联网搜索补充外部信息，杜绝大模型幻觉编造。
- 📊 完整检索量化评估体系
内置 20 组标准查询 + 28 份含干扰测试文档，一键生成评测报告，直观对比「向量 / BM25 / RRF」三种检索策略优劣。
- 🧱 高可扩展工程架构
业务分层清晰、模块完全解耦，预留完整扩展接口，可直接无缝升级 GraphRAG 知识图谱多跳问答。

---
🛠 技术栈
模块
技术选型
后端服务
Python FastAPI + Uvicorn + Pydantic v2
前端框架
React18 + TypeScript + Vite + TailwindCSS
向量检索
InMemoryVectorStore（Pickle 持久化）
关键词检索
rank_bm25（BM25Okapi）
大模型生态
OpenAI / DeepSeek / 阿里云百炼 / 通义千问 / Ollama
外部搜索
DuckDuckGo 开源全网搜索

---
🧭 系统架构流程
用户提问
   ├─ 语义向量化 → 向量语义检索
   ├─ 文本分词   → BM25 关键词检索
   │
   └─ 双路结果 → RRF 算法融合排序
          ├─ 检索有效 → 拼接上下文 + LLM 流式问答
          └─ 检索为空 → 自动 DuckDuckGo 联网搜索兜底


---
🚀 快速启动
1. 安装依赖
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
npm install

2. 环境配置
cp .env.example backend/.env

编辑backend/.env 填入对应模型 Key：
# 推荐：阿里云百炼
BAILIAN_API_KEY=sk-xxx

# 可选 DeepSeek / OpenAI / 通义千问

3. 启动服务
# 启动后端  http://127.0.0.1:8000
cd backend
python main.py

# 启动前端  http://localhost:5173
npm run dev

4. 使用流程
1. 访问前端页面，进入系统配置，选择大模型并保存
2. 知识库管理上传 PDF / TXT / DOCX 文档
3. 智能问答页面进行多轮文档对话

---
📈 检索效果评估
项目内置完整评测脚本，自动对比三种检索方案召回率：
cd backend
python evaluation/evaluate.py

评测输出示例：
Query                             向量    BM25     RRF
NNLM与RNN梯度消失                   0%    100%    100%
PyTorch比TensorFlow优势             0%    100%    100%
────────────────────────────────────────────────
平均 Recall@2                     90%    100%    100%

RRF 优于纯向量: +11%


---
⚙️ 核心参数配置
参数
默认值
说明
Top-K
4
单次检索返回文本片段数
相似度阈值
0.03
向量过滤阈值
分块大小
512
文档切片字符数
分块重叠
50
切片重叠字符，防止上下文断裂

---
📁 项目结构
rag-knowledge-qa/
├── backend/                # 后端主服务
│   ├── api/               # 路由接口
│   ├── core/              # 核心检索、LLM、文档、搜索逻辑
│   ├── models/            # 数据模型
│   ├── evaluation/        # 检索评估脚本
│   └── data/              # 向量持久化数据
├── src/                   # 前端源码
│   ├── pages/             # 问答/配置/知识库页面
│   ├── components/        # 公共组件
│   ├── services/          # 接口请求
│   └── stores/            # 全局状态
└── dist/                  # 前端打包产物

---
🚀 进阶迭代规划（GraphRAG 升级方向）
- 下一步：接入 Neo4j 实现 GraphRAG：自动抽取实体与关系、构建知识图谱、支持多跳推理问答
- 接入 Rerank 重排模型，进一步提升检索精度
- Docker 一键部署、多用户权限系统、知识库分类管理

---
📄 License
MIT License · Free for personal and commercial use
