"""
GraphRAG 检索器 - 图谱检索核心逻辑

流程：
1. 用户问题 → EntityExtractor 抽取出关键实体
2. 实体名 → KnowledgeGraph.search_entity 模糊匹配图节点
3. 匹配节点 → BFS 子图提取
4. 子图 → 格式化为文本 → 注入 LLM 上下文

与现有向量检索、BM25检索并行，结果通过 RRF 融合。
"""
import os
from typing import List, Optional
import networkx as nx

from core.graphrag.graph_store import KnowledgeGraph
from core.graphrag.entity_extractor import EntityExtractor


class GraphRetriever:
    """
    图谱检索器 - 整合实体抽取和图检索
    """

    def __init__(self):
        self.graph = KnowledgeGraph()
        self.extractor = EntityExtractor()

    async def index_document(self, chunks: List[str],
                             source_doc: str = "",
                             chunk_ids: Optional[List[str]] = None):
        """
        处理文档：对每个 chunk 抽取实体关系，存入图谱

        Args:
            chunks: 文本块列表
            source_doc: 来源文档名
            chunk_ids: 对应的chunk ID列表
        """
        total_triples = 0
        for i, chunk_text in enumerate(chunks):
            chunk_id = chunk_ids[i] if chunk_ids else f"{source_doc}_{i}"
            triples = await self.extractor.extract_from_document(
                chunk_text, chunk_id=chunk_id, source_doc=source_doc
            )
            if triples:
                self.graph.add_triples(triples, source_doc=source_doc)
                total_triples += len(triples)

        print(f"[GraphRAG] 文档 '{source_doc}' 抽取了 {total_triples} 条三元组")
        return total_triples

    async def search(self, query: str, top_k: int = 5,
                     max_depth: int = 2) -> tuple:
        """
        图谱检索主入口

        Args:
            query: 用户问题
            top_k: 返回子图中保留的节点数上限
            max_depth: BFS 遍历深度

        Returns:
            (formatted_text: str, subgraph: nx.MultiDiGraph, entities: List[str])
        """
        # 1. 从 query 中抽取实体
        entities = await self.extractor.extract_from_query(query)

        if not entities:
            # 尝试直接从 query 中提取关键词
            import re
            words = re.findall(r'[A-Z][a-zA-Z0-9]*', query)
            entities = list(set(words))[:5]

        if not entities:
            return "", nx.MultiDiGraph(), []

        # 2. 图检索
        formatted_text, subgraph = self.graph.query(
            entities, max_depth=max_depth, top_k=top_k
        )

        return formatted_text, subgraph, entities

    def delete_document(self, source_doc: str):
        """删除文档相关的所有图数据"""
        # 删除节点和边（通过 source_doc 属性标记）
        self.graph._ensure_loaded()
        nodes_to_remove = []
        for node_id, data in self.graph.graph.nodes(data=True):
            if source_doc in data.get('source_doc', ''):
                nodes_to_remove.append(node_id)

        for node_id in nodes_to_remove:
            self.graph.graph.remove_node(node_id)

        self.graph._save()
        if nodes_to_remove:
            print(f"[GraphRAG] 删除了 {len(nodes_to_remove)} 个实体节点 (来源: {source_doc})")

    def get_stats(self) -> dict:
        return self.graph.get_stats()

    async def close(self):
        await self.extractor.close()
