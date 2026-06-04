"""
文档处理引擎 - 负责解析TXT/PDF/Word文件并进行文本分块
"""
import os
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

from models.schemas import FileType, DocumentModel, DocumentStatus


class DocumentChunk:
    """文档块"""
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.content = content
        self.metadata = metadata


class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def process_file(self, file_path: str, original_name: str) -> tuple[List[DocumentChunk], Dict]:
        """
        处理文件：解析 → 清洗 → 分块
        
        返回: (文档块列表, 文档元数据)
        """
        # 判断文件类型
        file_type = self._detect_file_type(original_name)
        
        # 根据类型选择解析器
        text = self._parse_file(file_path, file_type)
        
        if not text:
            raise ValueError(f"无法从文件中提取文本内容: {original_name}")
        
        # 文本清洗
        text = self._clean_text(text)
        
        # 生成分块
        chunks = self._smart_chunk(text, {
            "source_id": str(uuid.uuid4()),
            "filename": original_name,
            "file_type": file_type.value,
            "chunk_index": 0
        })
        
        return chunks, {
            "filename": original_name,
            "file_type": file_type.value,
            "chunk_count": len(chunks)
        }
    
    def _detect_file_type(self, filename: str) -> FileType:
        """检测文件类型"""
        ext = Path(filename).suffix.lower()
        type_map = {
            ".txt": FileType.TXT,
            ".pdf": FileType.PDF,
            ".docx": FileType.DOCX
        }
        return type_map.get(ext, FileType.TXT)
    
    def _parse_file(self, file_path: str, file_type: FileType) -> str:
        """根据文件类型解析文本"""
        if file_type == FileType.TXT:
            return self._parse_txt(file_path)
        elif file_type == FileType.PDF:
            return self._parse_pdf(file_path)
        elif file_type == FileType.DOCX:
            return self._parse_docx(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {file_type}")
    
    def _parse_txt(self, path: str) -> str:
        """读取TXT文件，自动检测编码"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        for enc in encodings:
            try:
                with open(path, 'r', encoding=enc) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError("无法解码文本文件")
    
    def _parse_pdf(self, path: str) -> str:
        """解析PDF文件"""
        try:
            import pdfplumber
            text_parts = []
            with pdfplumber.open(path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"[第{i+1}页]\n{page_text}")
            return "\n\n".join(text_parts)
        except ImportError:
            # 回退到PyPDF2
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(path)
                text_parts = []
                for i, page in enumerate(reader.pages):
                    text_parts.append(f"[第{i+1}页]\n{page.extract_text() or ''}")
                return "\n\n".join(text_parts)
            except Exception as e:
                raise ValueError(f"PDF解析失败: {e}")
    
    def _parse_docx(self, path: str) -> str:
        """解析Word文档"""
        try:
            from docx import Document
            doc = Document(path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except ImportError:
            raise ValueError("请安装python-docx库以支持Word文档解析")
    
    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        # 去除多余空白但保留段落结构
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            cleaned = line.strip()
            if cleaned:
                cleaned_lines.append(cleaned)
            elif cleaned_lines:  # 保留空行作为段落分隔
                cleaned_lines.append('')
        
        result = '\n'.join(cleaned_lines)
        # 去除连续多个空行
        while '\n\n\n' in result:
            result = result.replace('\n\n\n', '\n\n')
        return result.strip()
    
    def _smart_chunk(self, text: str, base_metadata: Dict) -> List[DocumentChunk]:
        """
        智能分段策略：
        - 优先按段落分割
        - 超长段落按句子切分
        - 保持chunk_overlap避免语义断裂
        """
        chunks = []
        
        # 按双换行分割段落
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        chunk_index = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # 如果当前块加上新段落后不超过大小限制
            if len(current_chunk) + len(para) + 1 <= self.chunk_size:
                current_chunk = (current_chunk + "\n" + para).strip()
            else:
                # 保存当前块
                if current_chunk and len(current_chunk) > 10:
                    metadata = base_metadata.copy()
                    metadata["chunk_index"] = chunk_index
                    chunks.append(DocumentChunk(current_chunk, metadata))
                    chunk_index += 1
                
                # 如果单个段落就超过限制，需要进一步分割
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_long_text(para, base_metadata, chunk_index)
                    chunks.extend(sub_chunks)
                    chunk_index += len(sub_chunks)
                    current_chunk = ""
                else:
                    current_chunk = para
        
        # 处理最后一个块
        if current_chunk and len(current_chunk) > 10:
            metadata = base_metadata.copy()
            metadata["chunk_index"] = chunk_index
            chunks.append(DocumentChunk(current_chunk, metadata))
        
        return chunks
    
    def _split_long_text(self, text: str, base_metadata: Dict, start_index: int) -> List[DocumentChunk]:
        """将超长文本按句子分割"""
        chunks = []
        sentences = text.replace('。', '。\n').replace('！', '!\n').replace('？', '?\n').split('\n')
        
        current = ""
        chunk_idx = start_index
        
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            
            if len(current) + len(sent) <= self.chunk_size:
                current = (current + sent).strip()
            else:
                if current:
                    metadata = base_metadata.copy()
                    metadata["chunk_index"] = chunk_idx
                    chunks.append(DocumentChunk(current, metadata))
                    chunk_idx += 1
                current = sent
        
        if current:
            metadata = base_metadata.copy()
            metadata["chunk_index"] = chunk_idx
            chunks.append(DocumentChunk(current, metadata))
        
        return chunks
