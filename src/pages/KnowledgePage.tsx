import { useState, useEffect, useCallback } from 'react';
import {
  Upload,
  FileText,
  FileIcon as FilePdf,
  FileType,
  Trash2,
  RefreshCw,
  Database,
  Files,
  HardDrive,
  CheckCircle,
  Loader2,
  AlertCircle,
  XCircle
} from 'lucide-react';
import toast from 'react-hot-toast';
import type { Document, DocumentStatus } from '../types';
import { useAppStore } from '../stores/useAppStore';

const KnowledgePage: React.FC = () => {
  const {
    documents,
    documentsLoading,
    stats,
    loadDocuments,
    uploadFile,
    deleteDocument,
    loadStats
  } = useAppStore();

  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
    loadStats();
  }, []);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await handleFileUpload(e.dataTransfer.files[0]);
    }
  }, []);

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await handleFileUpload(e.target.files[0]);
      e.target.value = '';
    }
  };

  const handleFileUpload = async (file: File) => {
    const allowedTypes = ['.txt', '.pdf', '.docx'];
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!allowedTypes.includes(fileExt)) {
      toast.error(`不支持的文件类型: ${fileExt}，请上传TXT/PDF/Word文件`);
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      toast.error('文件大小超过50MB限制');
      return;
    }

    setUploading(true);
    try {
      await uploadFile(file);
      toast.success(`"${file.name}" 上传成功，正在处理...`);
    } catch (error: any) {
      toast.error(error.response?.data?.error || '上传失败，请重试');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId: string, fileName: string) => {
    if (!window.confirm(`确定要删除 "${fileName}" 吗？此操作不可撤销。`)) {
      return;
    }

    setDeletingId(docId);
    try {
      await deleteDocument(docId);
      toast.success('文档已删除');
    } catch (error) {
      toast.error('删除失败');
    } finally {
      setDeletingId(null);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (!bytes && bytes !== 0) return '未知';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return <FilePdf className="w-8 h-8 text-red-400" />;
      case 'docx':
        return <FileType className="w-8 h-8 text-blue-400" />;
      default:
        return <FileText className="w-8 h-8 text-slate-400" />;
    }
  };

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case 'indexed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400">
            <CheckCircle className="w-3 h-3" />
            已索引
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/15 text-amber-400">
            <Loader2 className="w-3 h-3 animate-spin" />
            处理中
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-500/15 text-red-400">
            <XCircle className="w-3 h-3" />
            失败
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white mb-2">知识库管理</h1>
        <p className="text-slate-400 text-sm">上传文档并构建可检索的知识库</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-cyan-500/10 to-transparent border border-cyan-500/20 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-500/20">
              <Files className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total_files || documents.length}</p>
              <p className="text-xs text-slate-400">文档总数</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-emerald-500/10 to-transparent border border-emerald-500/20 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-500/20">
              <Database className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">{stats.total_chunks || stats.db_total_chunks || 0}</p>
              <p className="text-xs text-slate-400">向量分块</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-violet-500/10 to-transparent border border-violet-500/20 rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-violet-500/20">
              <HardDrive className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-white">
                {(documents.reduce((acc: number, doc: Document) => acc + (doc.file_size || 0), 0) / (1024 * 1024)).toFixed(1)}MB
              </p>
              <p className="text-xs text-slate-400">总大小</p>
            </div>
          </div>
        </div>
      </div>

      {/* 文件上传区域 */}
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`
          relative border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-300 cursor-pointer
          ${dragActive
            ? 'border-cyan-400 bg-cyan-500/10 scale-[1.01]'
            : uploading
              ? 'border-amber-400 bg-amber-500/5'
              : 'border-slate-700 hover:border-slate-600 bg-slate-900/30 hover:bg-slate-800/30'
          }
        `}
      >
        <input
          type="file"
          accept=".txt,.pdf,.docx"
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={uploading}
        />

        <div className="space-y-3">
          {uploading ? (
            <>
              <Loader2 className="w-12 h-12 text-amber-400 mx-auto animate-spin" />
              <p className="text-white font-medium">正在上传...</p>
            </>
          ) : dragActive ? (
            <>
              <Upload className="w-12 h-12 text-cyan-400 mx-auto" />
              <p className="text-cyan-400 font-medium">释放文件以上传</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 mx-auto rounded-2xl bg-slate-800 flex items-center justify-center">
                <Upload className="w-7 h-7 text-slate-400" />
              </div>
              <div>
                <p className="text-white font-medium">拖放文件到此处或点击上传</p>
                <p className="text-sm text-slate-500 mt-1">支持 TXT、PDF、Word 格式，最大 50MB</p>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-center gap-2 mt-4">
          {['TXT', 'PDF', 'DOCX'].map((format) => (
            <span key={format} className="px-2.5 py-1 bg-slate-800 rounded-md text-xs text-slate-400 font-mono">
              .{format.toLowerCase()}
            </span>
          ))}
        </div>
      </div>

      {/* 文档列表 */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Files className="w-5 h-5 text-slate-400" />
            已上传文档
          </h2>

          <button
            onClick={() => { loadDocuments(); loadStats(); }}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${documentsLoading ? 'animate-spin' : ''}`} />
            刷新
          </button>
        </div>

        {documentsLoading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center py-16 bg-slate-900/50 rounded-2xl border border-dashed border-slate-800">
            <FileText className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-500">暂无文档</p>
            <p className="text-sm text-slate-600 mt-1">上传你的第一个文档开始使用</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="group bg-slate-900/50 backdrop-blur-sm border border-slate-800 rounded-xl p-4 hover:border-slate-700 transition-all duration-200"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-slate-800">
                      {getFileIcon(doc.file_type)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-white truncate max-w-[180px]" title={doc.original_name}>
                        {doc.original_name}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">{formatFileSize(doc.file_size)}</p>
                    </div>
                  </div>

                  <button
                    onClick={() => handleDelete(doc.id, doc.original_name)}
                    disabled={deletingId === doc.id}
                    className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg hover:bg-red-500/10 text-slate-500 hover:text-red-400 transition-all"
                  >
                    {deletingId === doc.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Trash2 className="w-4 h-4" />
                    )}
                  </button>
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-slate-800/50">
                  {getStatusBadge(doc.status)}

                  {doc.chunk_count > 0 && (
                    <span className="text-xs text-slate-500">
                      {doc.chunk_count} 个分块
                    </span>
                  )}
                </div>

                {doc.error_message && (
                  <p className="mt-2 text-xs text-red-400 flex items-start gap-1">
                    <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    {doc.error_message.length > 50 ? doc.error_message.substring(0, 50) + '...' : doc.error_message}
                  </p>
                )}

                <p className="mt-2 text-xs text-slate-600">
                  {new Date(doc.upload_time).toLocaleString('zh-CN')}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default KnowledgePage;
