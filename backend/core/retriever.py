"""
检索引擎与RAG管道 - 核心RAG逻辑实现

使用纯Python实现向量存储和检索（ChromaDB因Windows兼容性不可用时）。
支持 pickle 二进制持久化、余弦相似度搜索、BM25 混合检索。
"""
import uuid
import json
import math
import os
import pickle
import re
from typing import AsyncGenerator, List, Tuple, Optional
from datetime import datetime

from core.config import ConfigManager
from core.document_processor import DocumentProcessor, DocumentChunk
from core.llm_manager import LLMManager
from core.web_search import get_web_search_agent
from models.schemas import (
    AppConfig, MessageModel, MessageRole, AnswerMode,
    SourceReference, SearchResultItem, ChatRequest
)


# ====== 纯Python内存向量存储（零依赖，pickle持久化）======

class InMemoryVectorStore:
    """
    纯Python内存向量存储

    使用余弦相似度进行检索，pickle 二进制持久化（比JSON快10-100倍）。
    完全不依赖任何C扩展库。
    """

    def __init__(self, persist_path: str = "./data/vector_store.pkl"):
        self.persist_path = persist_path
        self.vectors: List[dict] = []  # 每项: {id, embedding, content, metadata}
        self._loaded = False

    def _ensure_loaded(self):
        """延迟加载持久化数据"""
        if self._loaded:
            return
        self._loaded = True

        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'rb') as f:
                    self.vectors = pickle.load(f)
                print(f"[VectorStore] 从文件加载了 {len(self.vectors)} 条向量记录")
            except Exception as e:
                print(f"[VectorStore] 加载失败，使用空存储: {e}")
                self.vectors = []

    def _save(self):
        """持久化到文件（pickle二进制格式）"""
        try:
            os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
            with open(self.persist_path, 'wb') as f:
                pickle.dump(self.vectors, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            print(f"[VectorStore] 持久化失败: {e}")
    
    def upsert(self, ids: List[str], embeddings: List[List[float]],
               documents: List[str], metadatas: List[dict]):
        """插入或更新向量"""
        self._ensure_loaded()
        
        existing_ids = {v['id'] for v in self.vectors}
        
        for i, doc_id in enumerate(ids):
            record = {
                'id': doc_id,
                'embedding': embeddings[i],
                'content': documents[i],
                'metadata': metadatas[i]
            }
            
            if doc_id in existing_ids:
                # 更新现有记录
                for idx, v in enumerate(self.vectors):
                    if v['id'] == doc_id:
                        self.vectors[idx] = record
                        break
            else:
                self.vectors.append(record)
        
        self._save()
        print(f"[VectorStore] upsert完成，共 {len(self.vectors)} 条")
    
    def delete_by_source(self, source_id: str):
        """删除指定来源的所有向量"""
        self._ensure_loaded()
        before = len(self.vectors)
        self.vectors = [v for v in self.vectors 
                       if v.get('metadata', {}).get('source_id') != source_id]
        deleted = before - len(self.vectors)
        if deleted > 0:
            self._save()
            print(f"[VectorStore] 删除了 {deleted} 条记录 (source={source_id})")
    
    def query(self, query_embedding: List[float], top_k: int = 4) -> dict:
        """
        余弦相似度搜索
        
        返回: {'ids': [[...]], 'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
        """
        self._ensure_loaded()
        
        if not self.vectors:
            return {'ids': [[]], 'documents': [[]], 'metadatas': [[]], 'distances': [[]]}
        
        # 计算所有向量的余弦相似度
        scored = []
        query_norm = math.sqrt(sum(x * x for x in query_embedding))
        
        for vec in self.vectors:
            emb = vec['embedding']
            emb_norm = math.sqrt(sum(x * x for x in emb))
            
            if query_norm > 0 and emb_norm > 0:
                dot = sum(q * e for q, e in zip(query_embedding, emb))
                similarity = dot / (query_norm * emb_norm)
            else:
                similarity = 0.0
            
            # ChromaDB返回的是距离（1 - similarity）
            distance = 1.0 - similarity
            
            scored.append((distance, vec))
        
        # 按距离排序（从小到大=最相似排最前）
        scored.sort(key=lambda x: x[0])
        
        # 取top_k
        top = scored[:top_k]
        
        return {
            'ids': [[t[1]['id'] for t in top]],
            'documents': [[t[1]['content'] for t in top]],
            'metadatas': [[t[1]['metadata'] for t in top]],
            'distances': [[t[0] for t in top]]
        }
    
    def count(self) -> int:
        """返回向量总数"""
        self._ensure_loaded()
        return len(self.vectors)
    
    def get(self, where: Optional[dict] = None) -> Optional[dict]:
        """按条件获取向量"""
        self._ensure_loaded()
        
        if not where:
            return {
                'ids': [v['id'] for v in self.vectors],
                'documents': [v['content'] for v in self.vectors],
                'metadatas': [v['metadata'] for v in self.vectors]
            }
        
        results = []
        for v in self.vectors:
            match = True
            for key, val in where.items():
                if v.get('metadata', {}).get(key) != val:
                    match = False
                    break
            if match:
                results.append(v)
        
        if not results:
            return None
        
        return {
            'ids': [v['id'] for v in results],
            'documents': [v['content'] for v in results],
            'metadatas': [v['metadata'] for v in results]
        }
    
    def delete(self, ids: List[str]):
        """按ID删除向量"""
        self._ensure_loaded()
        id_set = set(ids)
        before = len(self.vectors)
        self.vectors = [v for v in self.vectors if v['id'] not in id_set]
        if len(self.vectors) != before:
            self._save()


# ====== BM25 关键词检索引擎 ======

class BM25Index:
    """
    BM25 关键词检索引擎

    基于 rank_bm25 实现，提供关键词层面的检索能力。
    与向量检索形成双路互补：向量负责语义，BM25负责精确匹配。
    """

    def __init__(self):
        self._index = None
        self._documents: List[tuple] = []  # [(content, metadata), ...]
        self._dirty = True

    def _tokenize(self, text: str) -> List[str]:
        """中文+英文混合分词"""
        # 中文单字+双字
        tokens = []
        chinese_chars = re.findall(r'[一-鿿]+', text)
        for cc in chinese_chars:
            tokens.extend(list(cc))  # 单字
            for i in range(len(cc) - 1):
                tokens.append(cc[i:i+2])  # 双字

        # 英文单词
        tokens.extend(w.lower() for w in re.findall(r'[a-zA-Z][a-zA-Z0-9]*', text))
        # 数字
        tokens.extend(re.findall(r'\d+(?:\.\d+)?', text))

        return [t for t in tokens if len(t) > 0]

    def rebuild(self, vectors: List[dict]):
        """从向量存储重建BM25索引"""
        from rank_bm25 import BM25Okapi

        self._documents = [(v['content'], v['metadata']) for v in vectors]
        tokenized_corpus = [self._tokenize(doc[0]) for doc in self._documents]

        if tokenized_corpus:
            self._index = BM25Okapi(tokenized_corpus)
        else:
            self._index = None
        self._dirty = False

    def mark_dirty(self):
        """标记索引需要重建"""
        self._dirty = True

    def search(self, query: str, top_k: int = 4) -> List[dict]:
        """
        BM25搜索

        Returns: [{content, metadata, bm25_score}, ...]
        """
        if not self._index or self._dirty:
            return []

        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []

        try:
            scores = self._index.get_scores(tokenized_query)
        except Exception:
            return []

        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1], reverse=True)

        results = []
        for idx, score in indexed[:top_k]:
            if score > 0:
                results.append({
                    'content': self._documents[idx][0],
                    'metadata': self._documents[idx][1],
                    'bm25_score': float(score),
                })
        return results


# ====== ChromaDB包装器（跨平台备用）======

class ChromaDBWrapper:
    """ChromaDB适配器，提供与InMemoryVectorStore相同的接口"""
    
    def __init__(self):
        self._client = None
        self._collection = None
        self._available = False
    
    def _init_client(self):
        if self._client is not None:
            return
        
        try:
            import chromadb
            from chromadb import Settings as ChromaSettings
            
            persist_dir = "./data/chroma_db"
            os.makedirs(persist_dir, exist_ok=True)
            
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self._collection = self._client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            self._available = True
            print("[Retriever] 使用 ChromaDB 向量存储")
        except Exception as e:
            print(f"[Retriever] ChromaDB 初始化失败: {e}")
            print("[Retriever] 将使用纯Python内存向量存储作为Fallback")
            self._available = False
            raise
    
    def upsert(self, ids, embeddings, documents, metadatas):
        self._init_client()
        self._collection.upsert(
            ids=ids, embeddings=embeddings,
            documents=documents, metadatas=metadatas
        )
    
    def delete_by_source(self, source_id):
        self._init_client()
        try:
            results = self._collection.get(where={"source_id": source_id})
            if results and results.get('ids'):
                self._collection.delete(ids=results['ids'])
        except Exception as e:
            print(f"删除文档出错: {e}")
    
    def query(self, query_embedding, top_k=4):
        self._init_client()
        return self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
    
    def count(self):
        self._init_client()
        return self._collection.count()
    
    def get(self, where=None):
        self._init_client()
        return self._collection.get(where=where)
    
    def delete(self, ids):
        self._init_client()
        self._collection.delete(ids=ids)


# ====== 检索引擎（自动选择后端）======

class Retriever:
    """检索引擎 - 向量 + BM25 双路召回"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self._store = None
        self.bm25 = BM25Index()

    def _get_store(self):
        if self._store is not None:
            return self._store
        self._store = InMemoryVectorStore()
        print("[Retriever] 使用纯Python内存向量存储")
        return self._store

    def add_documents(self, chunks: List[DocumentChunk], embeddings: List[List[float]]):
        store = self._get_store()
        ids = [f"{chunk.metadata['source_id']}_{chunk.metadata['chunk_index']}" for chunk in chunks]
        store.upsert(
            ids=ids, embeddings=embeddings,
            documents=[chunk.content for chunk in chunks],
            metadatas=[chunk.metadata for chunk in chunks]
        )
        self.bm25.mark_dirty()

    def delete_document(self, source_id: str):
        store = self._get_store()
        store.delete_by_source(source_id)
        self.bm25.mark_dirty()

    def _ensure_bm25_built(self):
        if self.bm25._dirty:
            store = self._get_store()
            store._ensure_loaded()
            self.bm25.rebuild(store.vectors)

    def search(self, query_embedding: List[float], query_text: str = "",
               top_k: int = 4, threshold: float = 0.7) -> Tuple[List[dict], bool]:
        """双路召回：向量检索 + BM25 - RRF 合并"""
        store = self._get_store()
        self._ensure_bm25_built()

        try:
            fetch_k = max(top_k * 3, 12)
            vec_results = store.query(query_embedding, top_k=fetch_k)
            bm25_results = self.bm25.search(query_text, top_k=fetch_k)

            K = 60
            score_map = {}

            for rank, (doc_id, content, meta) in enumerate(zip(
                vec_results['ids'][0], vec_results['documents'][0],
                vec_results['metadatas'][0]
            )):
                key = content[:100]
                vec_sim = 1 - vec_results['distances'][0][rank]
                if vec_sim < 0.1:
                    continue
                score_map[key] = {
                    'id': doc_id, 'content': content, 'metadata': meta,
                    'rrf': 1.0 / (K + rank)
                }

            for rank, bm25_item in enumerate(bm25_results):
                key = bm25_item['content'][:100]
                if key not in score_map:
                    score_map[key] = {
                        'id': bm25_item['metadata'].get('source_id', ''),
                        'content': bm25_item['content'],
                        'metadata': bm25_item['metadata'],
                        'rrf': 0.0
                    }
                score_map[key]['rrf'] += 1.0 / (K + rank)

            if not score_map:
                return [], False

            ranked = sorted(score_map.values(), key=lambda x: x['rrf'], reverse=True)
            max_rrf = max(x['rrf'] for x in ranked) or 1.0

            final_results = []
            for item in ranked[:top_k]:
                final_results.append({
                    'id': item['id'],
                    'content': item['content'],
                    'metadata': item['metadata'],
                    'similarity': item['rrf'] / max_rrf,
                })

            found_good = any(r['similarity'] >= threshold for r in final_results)
            return final_results, found_good

        except Exception as e:
            print(f"[Retriever] 搜索出错: {e}")
            return [], False

    def get_stats(self) -> dict:
        store = self._get_store()
        try:
            return {"total_chunks": store.count()}
        except Exception as e:
            print(f"[Retriever] 统计出错: {e}")
            return {"total_chunks": 0}



# ====== RAG管道 ======

class RAGPipeline:
    """RAG问答管道"""
    
    SYSTEM_PROMPT_LOCAL = """你是一个智能文档助手。你的任务是基于提供的文档内容来回答用户的问题。

规则：
1. 只依据提供的参考文档内容来回答问题
2. 如果文档中没有相关信息，明确告知用户
3. 引用具体的文档来源
4. 回答要准确、简洁、有条理
5. 使用中文回答"""

    SYSTEM_PROMPT_WEB = """你是一个智能搜索助手。你的任务是基于网络搜索的结果来回答用户的问题。

规则：
1. 基于搜索结果提供准确的信息
2. 在回答中标注信息来源（标题和链接）
3. 对搜索结果进行综合分析和总结
4. 如果搜索结果不够全面，说明局限性
5. 使用中文回答"""
    
    def __init__(self):
        self.retriever = Retriever()
        self.document_processor = DocumentProcessor()
        self.llm_manager = LLMManager()
        self.config_manager = ConfigManager()
    
    async def query(self, request: ChatRequest,
                    conversation_history: List[MessageModel] = None) -> AsyncGenerator[dict, None]:
        config = self.config_manager.load_config()
        question = request.message
        
        # Step 1: 问题向量化
        try:
            question_embedding = await self.llm_manager.get_embedding(question)
        except Exception as e:
            yield {
                "token": f"Embedding生成失败: {str(e)}",
                "mode": "error",
                "sources": [],
                "search_results": []
            }
            return
        
        # Step 2: 向量检索
        search_results, has_good_match = self.retriever.search(
            query_embedding=question_embedding,
            query_text=question,
            top_k=config.retrieval_top_k,
            threshold=config.similarity_threshold
        )
        
        # Step 3: 决定模式 - 先搜文档，没有则自动联网搜索
        if has_good_match and search_results:
            # 文档有相关内容，只用文档回答
            mode = AnswerMode.LOCAL
            context = self._build_local_context(search_results)
            sources = self._extract_sources(search_results)
            system_prompt = self.SYSTEM_PROMPT_LOCAL
            search_result_items = []
        else:
            # 文档没有，自动联网搜索
            mode = AnswerMode.WEB
            web_agent = get_web_search_agent()
            web_results = await web_agent.search(question)
            
            if web_results:
                context = web_agent.format_context_for_llm(web_results)
                search_result_items = web_results
            else:
                context = "未找到相关的网络搜索结果。"
                search_result_items = []
            
            sources = []
            system_prompt = self.SYSTEM_PROMPT_WEB
        
        # Step 4 & 5: 构建消息并流式生成
        messages = self._build_messages(system_prompt, context, question, conversation_history or [])
        
        full_response = ""
        async for token in self.llm_manager.chat_stream(messages):
            full_response += token
            yield {
                "token": token,
                "mode": mode.value,
                "sources": sources if mode == AnswerMode.LOCAL else [],
                "search_results": [r.model_dump() for r in search_result_items] if mode == AnswerMode.WEB else []
            }
    
    def _build_local_context(self, search_results: List[dict]) -> str:
        context_parts = ["以下是从文档库中检索到的相关内容：\n"]
        
        for i, result in enumerate(search_results, 1):
            meta = result['metadata']
            source_file = meta.get('filename', '未知')
            page_info = f"，第{meta.get('page_number', '?')}页" if meta.get('page_number') else ""
            
            context_parts.append(
                f"\n--- 参考资料{i}（来源: {source_file}{page_info}，相关度: {result['similarity']:.2f}）---\n"
                f"{result['content']}\n"
            )
        
        context_parts.append("\n请严格基于以上参考资料回答用户的问题。")
        return "".join(context_parts)
    
    def _extract_sources(self, search_results: List[dict]) -> List[SourceReference]:
        sources = []
        for result in search_results:
            meta = result['metadata']
            source = SourceReference(
                document_id=meta.get('source_id', ''),
                document_name=meta.get('filename', '未知'),
                content=result['content'][:300],
                page_number=meta.get('page_number'),
                relevance_score=result['similarity']
            )
            sources.append(source)
        return sources
    
    def _build_messages(self, system_prompt: str, context: str,
                        question: str, history: List[MessageModel]) -> list:
        messages = [{"role": "system", "content": system_prompt}]
        
        recent_history = history[-10:] if history else []
        for msg in recent_history:
            messages.append({"role": msg.role.value, "content": msg.content})
        
        messages.append({"role": "user", "content": f"{context}\n\n用户问题: {question}"})
        return messages
    
    async def process_uploaded_file(self, file_path: str,
                                    original_name: str) -> Tuple[int, str]:
        config = self.config_manager.load_config()
        
        self.document_processor.chunk_size = config.chunk_size
        self.document_processor.chunk_overlap = config.chunk_overlap
        
        chunks, meta = self.document_processor.process_file(file_path, original_name)
        source_id = meta.get('source_id', str(uuid.uuid4()))
        
        for chunk in chunks:
            chunk.metadata['source_id'] = source_id
        
        # 生成embedding（使用纯Python嵌入）
        all_embeddings = []
        for chunk in chunks:
            embedding = await self.llm_manager.get_embedding(chunk.content)
            all_embeddings.append(embedding)
        
        # 存入向量数据库
        self.retriever.add_documents(chunks, all_embeddings)
        
        return len(chunks), source_id
    
    def delete_document_from_db(self, source_id: str):
        self.retriever.delete_document(source_id)


# 全局单例
_rag_pipeline: Optional[RAGPipeline] = None

def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline
