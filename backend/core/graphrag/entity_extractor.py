"""
实体关系抽取器 - 基于 LLM 从文档中抽取三元组

两种模式：
1. 文档处理：从文档 chunk 中抽取实体关系，用于构建知识图谱
2. 查询处理：从用户问题中抽取关键实体，用于图检索定位
"""
import json
import re
from typing import List, Tuple, Optional
from core.config import ConfigManager
from core.llm_manager import LLMManager


# 从文档中抽取实体关系的系统提示
SYSTEM_EXTRACT = """你是一个实体关系抽取助手。从以下文本中抽取实体及其关系。

要求：
1. 只抽取文本中明确出现的实体和关系
2. 实体包括：技术概念、算法模型、人物、组织、产品、专业术语等
3. 关系包括：提出、属于、衍生出、基于、包含、应用、对比、组成、用于等
4. 以JSON数组格式输出，每条格式：{"entity1": "名称", "relation": "关系", "entity2": "名称", "type": "entity1的类型"}
5. 如果没有实体关系，返回空数组 []

示例输出：
[
  {"entity1": "Transformer", "relation": "提出", "entity2": "Vaswani等人", "type": "技术"},
  {"entity1": "BERT", "relation": "基于", "entity2": "Transformer", "type": "模型"},
  {"entity1": "自注意力", "relation": "属于", "entity2": "Transformer", "type": "概念"}
]

只输出JSON数组，不要其他文字。"""

# 从用户查询中抽取关键词的系统提示
SYSTEM_QUERY_ENTITIES = """从以下用户问题中抽取出关键实体（技术名词、概念、术语、人名等）。

以JSON数组格式输出，每条：{"name": "实体名称", "type": "实体类型"}

示例：
问题：Transformer和BERT有什么关系？
输出：[{"name": "Transformer", "type": "技术"}, {"name": "BERT", "type": "模型"}]

只输出JSON数组，不要其他文字。"""


class EntityExtractor:
    """实体关系抽取器"""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.llm_manager = LLMManager()

    async def extract_from_document(self, text: str,
                                    chunk_id: str = "",
                                    source_doc: str = "") -> List[Tuple[str, str, str, str]]:
        """
        从文档文本中抽取实体关系三元组

        Returns: [(entity1, relation, entity2, type1), ...]
        """
        if not text or len(text) < 20:
            return []

        try:
            result = await self._call_llm_extract(SYSTEM_EXTRACT, text)
            triples = self._parse_triples(result)

            # 过滤规则：去重 + 过滤过短的实体名
            seen = set()
            filtered = []
            for e1, rel, e2, etype in triples:
                key = (e1.strip(), rel.strip(), e2.strip())
                if key not in seen and len(e1) >= 1 and len(e2) >= 1:
                    seen.add(key)
                    filtered.append((e1.strip(), rel.strip(), e2.strip(), etype.strip() or "未知"))
            return filtered

        except Exception as e:
            print(f"[EntityExtractor] 抽取失败: {e}")
            return []

    async def extract_from_query(self, query: str) -> List[str]:
        """
        从用户查询中抽取关键实体名称

        Returns: [entity_name, ...]
        """
        if not query or len(query) < 2:
            return []

        try:
            result = await self._call_llm_extract(SYSTEM_QUERY_ENTITIES, query)
            entities = self._parse_query_entities(result)
            return [e.strip() for e in entities if len(e.strip()) >= 1]
        except Exception as e:
            print(f"[EntityExtractor] 查询实体抽取失败: {e}")
            # 回退：提取引号内的词 + 专业术语
            return self._fallback_extract(query)

    async def _call_llm_extract(self, system_prompt: str, text: str) -> str:
        """调用 LLM 进行抽取"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text[:2000]},  # 截断避免超长
        ]

        # 使用 llm_manager 调用API
        config = self.config_manager.load_config()
        api_key = self.config_manager.get_api_key()
        if not api_key:
            raise ValueError("API Key 未配置")

        from core.llm_manager import PROVIDER_CONFIGS
        provider_id = config.provider.value
        base_url = config.custom_base_url or PROVIDER_CONFIGS.get(provider_id, {}).get("base_url", "")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": 0.1,  # 低温度提高抽取一致性
            "max_tokens": 1024,
            "stream": False,
        }

        import httpx
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                raise Exception(f"LLM API 返回 {response.status_code}: {response.text}")

    def _parse_triples(self, text: str) -> List[Tuple[str, str, str, str]]:
        """解析 LLM 返回的 JSON 三元组"""
        # 提取 JSON 数组
        json_match = re.search(r'\[.*?\]', text, re.DOTALL)
        if not json_match:
            return []

        try:
            data = json.loads(json_match.group())
            triples = []
            for item in data:
                if isinstance(item, dict):
                    e1 = item.get("entity1", item.get("subject", ""))
                    rel = item.get("relation", item.get("predicate", ""))
                    e2 = item.get("entity2", item.get("object", ""))
                    etype = item.get("type", item.get("entity1_type", "未知"))
                    if e1 and rel and e2:
                        triples.append((e1, rel, e2, etype))
            return triples
        except json.JSONDecodeError:
            return []

    def _parse_query_entities(self, text: str) -> List[str]:
        """解析查询实体"""
        json_match = re.search(r'\[.*?\]', text, re.DOTALL)
        if not json_match:
            return self._fallback_extract(text)

        try:
            data = json.loads(json_match.group())
            return [item.get("name", "") for item in data if isinstance(item, dict)]
        except json.JSONDecodeError:
            return self._fallback_extract(text)

    def _fallback_extract(self, text: str) -> List[str]:
        """回退方案：基于规则提取专业术语"""
        # 提取引号内的词
        quoted = re.findall(r'"([^"]+)"', text)

        # 提取英文技术名词（驼峰/大写组合）
        tech_terms = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:[-][A-Z][a-zA-Z0-9]*)*\b', text)

        # 中文专业术语（2-6字常见技术词，默认抽取较短的避免噪音）
        # 这里暂不处理，因为规则太复杂

        # 合并去重
        entities = list(set(quoted + tech_terms))
        # 过滤太短的
        return [e for e in entities if len(e) >= 2]

    async def close(self):
        await self.llm_manager.close()
