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
        "models": ["deepseek-chat", "deepseek-reasoner"]
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "models": []  # Ollama动态获取可用模型
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
        """获取文本的向量嵌入"""
        config = self.config_manager.load_config()
        
        # 方案1: 使用纯Python轻量级嵌入（无需任何外部运行时）
        try:
            from core.embeddings import get_embedding_function
            ef = get_embedding_function()
            result = ef.embed([text])
            return result[0]
        except Exception as e:
            print(f"本地纯Python Embedding失败: {e}")
        
        # 方案2: 尝试ChromaDB内置的DefaultEmbeddingFunction（需要onnxruntime）
        try:
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            ef = DefaultEmbeddingFunction()
            result = ef([text])
            vec = result[0]
            return vec.tolist() if hasattr(vec, 'tolist') else list(vec)
        except Exception as e:
            print(f"ChromaDB DefaultEmbeddingFunction失败: {e}")
        
        # 方案3: 回退到API方式
        provider_id = config.provider.value
        base_url = config.custom_base_url or PROVIDER_CONFIGS.get(provider_id, {}).get("base_url", "")
        
        if not config.api_key:
            raise ValueError(
                "Embedding生成失败。\n"
                "请先在【系统配置】页面填写AI模型的API Key后再上传文档。\n"
                "推荐使用 DeepSeek 或 OpenAI 的API Key。"
            )
        
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": config.embedding_model,
            "input": text
        }
        
        client = await self._get_client()
        response = await client.post(
            f"{base_url}/embeddings",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            return data["data"][0]["embedding"]
        else:
            raise Exception(f"Embedding API返回错误: {response.status_code}")
