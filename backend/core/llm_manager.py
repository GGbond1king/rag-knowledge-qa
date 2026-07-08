"""
LLM模型管理器 - 统一管理不同AI模型的调用
"""
import os
from typing import AsyncGenerator, Optional, Dict, Any
import httpx

from core.config import ConfigManager


# 提供商配置映射
PROVIDER_CONFIGS = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    "qwen": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-turbo", "qwen-plus", "qwen-max"]
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner", "deepseek-v4-flash", "deepseek-v3"]
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "models": []  # Ollama动态获取可用模型
    },
    "bailian": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["glm-5", "glm-4", "qwen-max", "qwen-plus", "qwen-turbo"]
    }
}


class LLMManager:
    """LLM管理器"""
    
    def __init__(self):
        self.config_manager = ConfigManager()
        self.client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建HTTP客户端"""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(timeout=120.0)
        return self.client
    
    async def close(self):
        """关闭HTTP客户端"""
        if self.client and not self.client.is_closed:
            await self.client.aclose()
    
    def get_config(self) -> Dict:
        """获取当前配置"""
        config = self.config_manager.load_config()
        provider_id = config.provider.value
        
        base_url = config.custom_base_url or PROVIDER_CONFIGS.get(provider_id, {}).get("base_url", "")
        
        return {
            "provider": provider_id,
            "api_key": config.api_key,
            "model": config.model,
            "base_url": base_url
        }
    
    async def chat_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> AsyncGenerator[str, None]:
        """
        流式调用聊天API
        
        Yields: token字符串
        """
        config = self.get_config()
        
        if not config["api_key"]:
            yield "错误：请先在系统设置中配置API Key"
            return
        
        payload = {
            "model": config["model"],
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        client = await self._get_client()
        
        try:
            async with client.stream(
                "POST",
                f"{config['base_url']}/chat/completions",
                json=payload,
                headers=headers
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"错误（HTTP {response.status_code}）: {error_text.decode()}"
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        data_str = line[6:]
                        try:
                            import json
                            data = json.loads(data_str)
                            delta = data.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
                    
        except Exception as e:
            yield f"请求失败: {str(e)}"
    
    async def get_embedding(self, text: str) -> list:
        """获取文本的向量嵌入（API优先，纯Python兜底）"""
        config = self.config_manager.load_config()
        api_key = self.config_manager.get_api_key()
        provider_id = config.provider.value

        # 没有Embedding接口的提供商直接跳过API方案
        NO_EMBED_PROVIDERS = {"deepseek", "ollama"}

        # 方案1: API嵌入（真正的语义向量，优先使用）
        if api_key and provider_id not in NO_EMBED_PROVIDERS:
            try:
                base_url = config.custom_base_url or PROVIDER_CONFIGS.get(provider_id, {}).get("base_url", "")
                if not base_url:
                    raise ValueError("未配置API地址")

                # Bailian / OpenAI 兼容嵌入API
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                # 模型名映射：bailian→text-embedding-v3，其他→config中配置的embedding_model
                embed_model = config.embedding_model
                if provider_id == "bailian" and embed_model in ("all-MiniLM-L6-v2", ""):
                    embed_model = "text-embedding-v3"

                payload = {"model": embed_model, "input": text}
                client = await self._get_client()
                response = await client.post(
                    f"{base_url}/embeddings", json=payload, headers=headers
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
                else:
                    print(f"API Embedding 返回 {response.status_code}，降级到本地方案")
            except Exception as e:
                print(f"API Embedding 失败: {e}，降级到本地方案")

        # 方案2: 纯Python轻量级嵌入（零依赖兜底）
        try:
            from core.embeddings import get_embedding_function
            ef = get_embedding_function()
            result = ef.embed([text])
            return result[0]
        except Exception as e:
            raise ValueError(
                f"Embedding 全部方案失败: {e}\n"
                "请检查API Key配置是否正确，或网络是否可访问。"
            )
