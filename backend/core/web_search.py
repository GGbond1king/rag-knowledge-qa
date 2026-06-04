"""
网络搜索代理 - 当本地知识库无法满足时进行网络搜索
"""
from typing import List, Optional
from duckduckgo_search import DDGS

from models.schemas import SearchResultItem


class WebSearchAgent:
    """网络搜索代理"""
    
    def __init__(self):
        self.ddgs = DDGS()
    
    async def search(
        self,
        query: str,
        num_results: int = 5,
        region: str = "cn-zh"
    ) -> List[SearchResultItem]:
        """
        执行网络搜索
        
        Args:
            query: 搜索关键词
            num_results: 返回结果数量
            region: 搜索区域
            
        Returns:
            搜索结果列表
        """
        try:
            results = self.ddgs.text(
                query,
                max_results=num_results,
                region=region
            )
            
            search_results = []
            for item in results:
                search_result = SearchResultItem(
                    title=item.get("title", ""),
                    url=item.get("href", ""),
                    snippet=item.get("body", "")[:500]  # 截断过长的摘要
                )
                search_results.append(search_result)
            
            return search_results
            
        except Exception as e:
            print(f"搜索失败: {e}")
            return []
    
    def format_context_for_llm(self, results: List[SearchResultItem]) -> str:
        """
        将搜索结果格式化为LLM可理解的上下文格式
        """
        if not results:
            return ""
        
        context_parts = ["以下是网络搜索到的相关信息：\n"]
        
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"{i}. **{result.title}**\n"
                f"   来源: {result.url}\n"
                f"   摘要: {result.snippet}\n"
            )
        
        context_parts.append(
            "\n请基于以上搜索结果回答用户的问题，并在回答中标注信息来源。"
        )
        
        return "\n".join(context_parts)


# 全局单例实例
_web_search_agent: Optional[WebSearchAgent] = None

def get_web_search_agent() -> WebSearchAgent:
    """获取全局WebSearchAgent实例"""
    global _web_search_agent
    if _web_search_agent is None:
        _web_search_agent = WebSearchAgent()
    return _web_search_agent
