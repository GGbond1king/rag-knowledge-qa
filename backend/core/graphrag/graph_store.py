"""
知识图谱存储 - 基于 NetworkX 的内存图数据库

支持实体节点、关系边的增删查，BFS 子图提取，pickle 持久化。
"""
import os
import json
import pickle
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

import networkx as nx


@dataclass
class EntityNode:
    """实体节点"""
    id: str
    name: str
    entity_type: str = "未知"         # 人物/技术/概念/组织/产品/算法
    source_doc: str = ""              # 来源文档
    chunk_ref: str = ""               # 来源 chunk ID
    description: str = ""             # 简短描述


@dataclass
class RelationEdge:
    """关系边"""
    source_id: str
    target_id: str
    relation: str                     # 关系类型：提出/属于/衍生出/包含/应用等
    weight: float = 1.0
    source_doc: str = ""


class KnowledgeGraph:
    """
    知识图谱 - 实体关系图存储

    基于 NetworkX 的有向图实现：
    - 节点 = 实体（概念、技术、人物等）
    - 边 = 关系（提出、属于、衍生出等）
    - 支持 BFS 子图提取、实体模糊匹配、pickle 持久化
    """

    def __init__(self, persist_path: str = "./data/knowledge_graph.pkl"):
        self.persist_path = persist_path
        self.graph = nx.MultiDiGraph()
        self._loaded = False

        # 实体名称 → node_id 索引（用于快速查找）
        self._name_index: Dict[str, str] = {}

    # ---- 持久化 ----

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._loaded = True
        if os.path.exists(self.persist_path):
            try:
                with open(self.persist_path, 'rb') as f:
                    data = pickle.load(f)
                    self.graph = data['graph']
                    self._name_index = data['name_index']
                print(f"[KnowledgeGraph] 加载 {self.graph.number_of_nodes()} 节点, "
                      f"{self.graph.number_of_edges()} 条关系")
            except Exception as e:
                print(f"[KnowledgeGraph] 加载失败: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)
        with open(self.persist_path, 'wb') as f:
            pickle.dump({
                'graph': self.graph,
                'name_index': self._name_index,
            }, f, protocol=pickle.HIGHEST_PROTOCOL)

    # ---- 节点操作 ----

    def _make_node_id(self, name: str) -> str:
        """生成稳定的节点 ID"""
        return hashlib.md5(name.encode('utf-8')).hexdigest()[:12]

    def add_entity(self, name: str, entity_type: str = "未知",
                   source_doc: str = "", chunk_ref: str = "",
                   description: str = "") -> str:
        """添加实体节点（重复名称自动去重）"""
        self._ensure_loaded()
        node_id = self._make_node_id(name)

        if node_id not in self.graph:
            self.graph.add_node(node_id, **{
                'name': name,
                'entity_type': entity_type,
                'source_doc': source_doc,
                'chunk_ref': chunk_ref,
                'description': description,
            })
            self._name_index[name] = node_id
        else:
            # 更新已有节点的元数据（追加文档来源）
            existing = self.graph.nodes[node_id]
            if source_doc and source_doc not in existing.get('source_doc', ''):
                existing['source_doc'] = existing.get('source_doc', '') + f"; {source_doc}"

        self._save()
        return node_id

    def add_relation(self, source_name: str, target_name: str,
                     relation: str, source_doc: str = "", weight: float = 1.0):
        """添加实体关系（自动创建实体节点）"""
        src_id = self.add_entity(source_name, source_doc=source_doc)
        tgt_id = self.add_entity(target_name, source_doc=source_doc)

        # 检查是否已有相同关系
        has_edge = False
        for _, _, data in self.graph.edges(src_id, data=True):
            if data.get('target_id') == tgt_id and data.get('relation') == relation:
                has_edge = True
                break

        if not has_edge:
            self.graph.add_edge(src_id, tgt_id, **{
                'relation': relation,
                'weight': weight,
                'source_doc': source_doc,
            })

        self._save()

    def add_triples(self, triples: List[Tuple[str, str, str, str]],
                    source_doc: str = ""):
        """
        批量添加三元组 (实体1, 关系, 实体2, 类型)

        triples: [(entity1, relation, entity2, type1), ...]
        """
        for triple in triples:
            if len(triple) >= 3:
                e1, rel, e2 = triple[0], triple[1], triple[2]
                e1_type = triple[3] if len(triple) > 3 else "未知"
                self.add_entity(e1, entity_type=e1_type, source_doc=source_doc)
                self.add_entity(e2, source_doc=source_doc)
                self.add_relation(e1, e2, rel, source_doc=source_doc)

    # ---- 查询 ----

    def search_entity(self, keyword: str, threshold: float = 0.3) -> List[dict]:
        """
        模糊匹配实体（基于名称包含关系）

        Returns: [{node_id, name, entity_type, score}, ...]
        """
        self._ensure_loaded()
        keyword_lower = keyword.lower()
        results = []

        for node_id, data in self.graph.nodes(data=True):
            name = data.get('name', '')
            name_lower = name.lower()

            # 精确包含
            if keyword_lower in name_lower:
                score = len(keyword) / max(len(name), 1)
                results.append({
                    'node_id': node_id,
                    'name': name,
                    'entity_type': data.get('entity_type', '未知'),
                    'score': min(score + 0.5, 1.0),  # 包含优先
                })
                continue

            # 字面重叠（中文）
            overlap = len(set(keyword_lower) & set(name_lower))
            char_score = overlap / max(len(set(keyword_lower)), 1)
            if char_score >= threshold:
                results.append({
                    'node_id': node_id,
                    'name': name,
                    'entity_type': data.get('entity_type', '未知'),
                    'score': char_score,
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:10]

    def get_subgraph(self, node_id: str, max_depth: int = 2,
                     max_nodes: int = 30) -> nx.MultiDiGraph:
        """
        BFS 提取子图（从指定节点出发，最大深度 max_depth）

        Args:
            node_id: 起始节点ID
            max_depth: BFS遍历深度
            max_nodes: 最大节点数（防止子图过大）

        Returns: 子图（MultiDiGraph）
        """
        self._ensure_loaded()
        if node_id not in self.graph:
            return nx.MultiDiGraph()

        # BFS 收集节点
        visited = {node_id}
        queue = [(node_id, 0)]
        sub_nodes = set()

        while queue:
            current, depth = queue.pop(0)
            sub_nodes.add(current)
            if depth >= max_depth:
                continue

            for neighbor in self.graph.predecessors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
            for neighbor in self.graph.successors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

            if len(sub_nodes) >= max_nodes:
                break

        return self.graph.subgraph(sub_nodes).copy()

    def format_subgraph_as_text(self, subgraph: nx.MultiDiGraph) -> str:
        """将子图格式化为 LLM 可理解的文本"""
        if subgraph.number_of_nodes() == 0:
            return ""

        lines = ["知识图谱中的实体关系："]

        # 实体列表
        for node_id, data in subgraph.nodes(data=True):
            etype = data.get('entity_type', '')
            type_str = f" ({etype})" if etype else ""
            lines.append(f"- 实体：{data.get('name', '')}{type_str}")

        # 关系列表
        lines.append("\n关系：")
        for src, tgt, data in subgraph.edges(data=True):
            src_name = subgraph.nodes[src].get('name', src)
            tgt_name = subgraph.nodes[tgt].get('name', tgt)
            rel = data.get('relation', '相关')
            lines.append(f"  {src_name} — [{rel}] → {tgt_name}")

        return "\n".join(lines)

    def query(self, query_entities: List[str], max_depth: int = 2,
              top_k: int = 5) -> Tuple[str, nx.MultiDiGraph]:
        """
        图形检索主入口

        1. 匹配 query 中的实体
        2. BFS 提取子图
        3. 格式化为文本

        Returns: (formatted_text, subgraph)
        """
        self._ensure_loaded()
        merged_graph = nx.MultiDiGraph()

        for entity_name in query_entities:
            matches = self.search_entity(entity_name)
            for match in matches[:3]:  # 每个 entity 取 top3 节点
                sub = self.get_subgraph(match['node_id'], max_depth=max_depth)
                merged_graph = nx.compose(merged_graph, sub)

        # 限制大小
        if merged_graph.number_of_nodes() > 50:
            # 按度中心性排序取 top50
            degrees = dict(merged_graph.degree())
            top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:50]
            merged_graph = merged_graph.subgraph([n[0] for n in top_nodes]).copy()

        text = self.format_subgraph_as_text(merged_graph)
        return text, merged_graph

    def get_stats(self) -> dict:
        """统计信息"""
        self._ensure_loaded()
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "entity_types": self._count_entity_types(),
        }

    def _count_entity_types(self) -> dict:
        counts = {}
        for _, data in self.graph.nodes(data=True):
            etype = data.get('entity_type', '未知')
            counts[etype] = counts.get(etype, 0) + 1
        return counts
