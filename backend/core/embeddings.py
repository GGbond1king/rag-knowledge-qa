"""
纯Python文本嵌入工具 - 零外部依赖

完全使用Python内置模块实现，不依赖numpy/onnxruntime/PyTorch等任何C扩展。
使用TF-IDF + 哈希投影方式生成固定维度向量，适用于文档检索场景。
"""

import re
import math
import hashlib
from typing import List, Dict, Optional


class LightweightEmbeddingFunction:
    """
    纯Python文本嵌入函数 - 零依赖版本
    
    原理：
    1. 文本预处理（中文n-gram分词 + 英文单词分词）
    2. 计算词频（TF）
    3. 通过哈希投影将每个token映射到固定维度的多个位置
    4. L2归一化
    
    不需要：numpy、onnxruntime、PyTorch、torch、sentence-transformers
    只需要：Python标准库 (re, math, hashlib)
    """
    
    STOP_WORDS = set([
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
        '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会',
        '着', '没有', '看', '好', '自己', '这', '那', '她', '他', '它', '们',
        '什么', '这个', '那个', '哪个', '如何', '为什么', '因为', '所以', '但是',
        '如果', '虽然', '或者', '以及', '等', '等等', '可以', '可能', '应该',
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
        'should', 'may', 'might', 'shall', 'can', 'need', 'dare', 'ought',
        'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
        'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
        'between', 'out', 'off', 'over', 'under', 'again', 'further', 'then',
        'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'each',
        'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just', 'that',
        'this', 'these', 'those', 'it', 'its', 'their', 'them', 'his', 'her',
        'she', 'we', 'they', 'our', 'your', 'my', 'i', 'me', 'us',
    ])
    
    CHINESE_PATTERN = re.compile(r'[\u4e00-\u9fff]+')
    WORD_PATTERN = re.compile(r'[a-zA-Z][a-zA-Z0-9]*')
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # 预计算的伪随机种子序列（用于哈希投影的一致性）
        self._seeds = [self._hash_seed(i) for i in range(dimension)]
    
    def _hash_seed(self, idx: int) -> int:
        """为每个维度生成确定性的伪随机种子"""
        h = hashlib.sha256(f"rag_embed_dim_{idx}".encode()).digest()
        return int.from_bytes(h[:4], 'little')
    
    def _tokenize(self, text: str) -> List[str]:
        """中文按字符n-gram切分 + 英文按单词提取"""
        tokens = []
        
        # 中文处理
        for match in self.CHINESE_PATTERN.findall(text):
            chars = list(match)
            tokens.extend(chars)  # 单字
            for i in range(len(chars) - 1):
                tokens.append(chars[i] + chars[i+1])  # 双字gram
                if i < len(chars) - 2:
                    tokens.append(chars[i] + chars[i+1] + chars[i+2])  # 三字gram
        
        # 英文处理
        tokens.extend(w.lower() for w in self.WORD_PATTERN.findall(text))
        
        # 数字
        tokens.extend(re.findall(r'\d+(?:\.\d+)?', text))
        
        # 过滤停用词和空串
        return [t for t in tokens if t not in self.STOP_WORDS and len(t) > 0]
    
    def _hash_to_vector(self, token: str, weight: float) -> List[float]:
        """将单个token通过多重哈希投影到向量空间
        
        每个token使用8个不同的哈希函数映射到向量中的不同位置，
        同时贡献正值或负值。这模拟了随机投影的效果。
        """
        vec = [0.0] * self.dimension
        num_hashes = 8
        
        for hash_idx in range(num_hashes):
            # 为每个token+hash_idx组合生成唯一哈希
            raw = hashlib.sha256(f"{token}_h{hash_idx}".encode()).digest()
            
            # 用哈希决定位置和符号
            pos_val = int.from_bytes(raw[0:4], 'little')
            sign_val = int.from_bytes(raw[4:8], 'little')
            
            position = pos_val % self.dimension
            sign = 1.0 if sign_val % 2 == 0 else -1.0
            
            # 归一化权重（基于token长度和哈希值）
            magnitude = weight * (0.5 + (sign_val % 256) / 512.0)
            
            vec[position] += sign * magnitude
        
        return vec
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本列表转换为向量列表"""
        results = []
        
        for text in texts:
            tokens = self._tokenize(text)
            
            if not tokens:
                # 空文本返回均匀分布的小值向量
                results.append([1e-7] * self.dimension)
                continue
            
            # 初始化向量
            vec = [0.0] * self.dimension
            
            # 对每个token计算权重并累加
            for token in tokens:
                # TF权重：出现次数越多权重越高（但非线性衰减）
                count_in_text = sum(1 for t in tokens if t == token)
                tf_weight = 1.0 / math.sqrt(count_in_text)
                
                # Token长度权重（长词通常更有意义）
                length_weight = min(len(token), 6) / 3.0
                
                total_weight = tf_weight * length_weight
                
                # 投影到向量空间
                contrib = self._hash_to_vector(token, total_weight)
                for i in range(self.dimension):
                    vec[i] += contrib[i]
            
            # L2归一化
            norm_sq = sum(x * x for x in vec)
            norm = math.sqrt(norm_sq) if norm_sq > 0 else 1.0
            
            if norm > 0:
                vec = [x / norm for x in vec]
            
            results.append(vec)
        
        return results
    
    def build_vocab_from_texts(self, texts: List[str]):
        """构建词表以提升后续嵌入质量（可选优化）"""
        # 纯哈希方案不需要显式构建词表，
        # 但可以通过统计词频来调整权重
        pass
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        return self.embed(texts)


# 全局单例
_embedding_function: Optional[LightweightEmbeddingFunction] = None


def get_embedding_function() -> LightweightEmbeddingFunction:
    global _embedding_function
    if _embedding_function is None:
        _embedding_function = LightweightEmbeddingFunction(dimension=384)
    return _embedding_function
