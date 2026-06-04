# RAG智能检索系统

基于检索增强生成（RAG）技术的智能问答系统，支持文档知识库管理和网络搜索。

## 功能特性

- 📄 **文档上传管理**: 支持 PDF、DOCX、TXT 格式文档
- 🔍 **智能问答**: 基于本地知识库的 RAG 问答
- 🌐 **网络搜索**: 本地知识库无结果时自动联网搜索
- 💬 **对话管理**: 支持多轮对话历史
- ⚙️ **灵活配置**: 支持多种 AI 模型提供商

## 技术栈

- **后端**: FastAPI + Python
- **前端**: React + TypeScript + Vite + TailwindCSS
- **向量数据库**: 纯Python内存向量存储（兼容ChromaDB）
- **AI模型**: 支持 OpenAI、DeepSeek、Qwen、Ollama

## 快速开始

### 1. 安装依赖

```bash
# 安装后端依赖
cd backend
pip install -r requirements.txt

# 安装前端依赖
cd ..
npm install
```

### 2. 配置

创建 `backend/.env` 文件：

```env
# AI模型配置
DEEPSEEK_API_KEY=your_api_key_here

# 或者使用其他提供商
# OPENAI_API_KEY=your_api_key_here
# QWEN_API_KEY=your_api_key_here
```

### 3. 启动

```bash
# 启动后端 (端口8000)
cd backend
python main.py

# 启动前端 (另一个终端)
npm run dev
```

访问 http://localhost:5173

## 项目结构

```
My_RAG/
├── backend/
│   ├── api/          # API路由
│   ├── core/         # 核心模块
│   ├── models/       # 数据模型
│   └── data/         # 数据存储
├── src/
│   ├── components/   # React组件
│   ├── pages/        # 页面
│   ├── services/     # API服务
│   └── stores/       # 状态管理
└── ...
```

## 配置说明

### AI模型提供商

系统支持多种AI模型提供商：

| 提供商 | 说明 | API Key |
|--------|------|---------|
| DeepSeek | 推荐，性价比较高 | deepseek-api-key |
| OpenAI | GPT系列模型 | openai-api-key |
| Qwen | 阿里通义千问 | qwen-api-key |
| Ollama | 本地模型 | 无需API Key |

### Embedding模型

- `all-MiniLM-L6-v2`: 通用英文模型，384维
- `multilingual-e5-large`: 中英双语，1024维
- `bge-large-zh-v1.5`: 中文优化，1024维

## License

MIT