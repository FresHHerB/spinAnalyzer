import { useState, useRef } from 'react';
import { Upload, File, CheckCircle, XCircle, Loader2, AlertCircle } from 'lucide-react';

interface UploadedFile {
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
  progress?: number;
}

export default function HandUploader() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFiles(droppedFiles);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      handleFiles(selectedFiles);
    }
  };

  const handleFiles = (newFiles: File[]) => {
    // Validate file types
    const validExtensions = ['.xml', '.txt', '.hh', '.zip'];
    const validFiles = newFiles.filter(file => {
      const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
      return validExtensions.includes(ext);
    });

    if (validFiles.length !== newFiles.length) {
      alert(`Alguns arquivos foram ignorados. Formatos aceitos: ${validExtensions.join(', ')}`);
    }

    const uploadedFiles: UploadedFile[] = validFiles.map(file => ({
      name: file.name,
      size: file.size,
      status: 'pending',
      progress: 0,
    }));

    setFiles(prev => [...prev, ...uploadedFiles]);

    // Simulate upload (in production, this would call an API)
    uploadedFiles.forEach((_, index) => {
      simulateUpload(files.length + index);
    });
  };

  const simulateUpload = (fileIndex: number) => {
    // Simulate upload progress
    const interval = setInterval(() => {
      setFiles(prev => {
        const newFiles = [...prev];
        const file = newFiles[fileIndex];

        if (!file || file.status !== 'pending' && file.status !== 'uploading') {
          clearInterval(interval);
          return prev;
        }

        if (file.status === 'pending') {
          file.status = 'uploading';
          file.progress = 0;
        }

        if (file.progress !== undefined && file.progress < 100) {
          file.progress += Math.random() * 30;
          if (file.progress >= 100) {
            file.progress = 100;
            // Simulate random success/failure
            if (Math.random() > 0.2) {
              file.status = 'success';
            } else {
              file.status = 'error';
              file.error = 'Erro ao processar arquivo';
            }
            clearInterval(interval);
          }
        }

        return newFiles;
      });
    }, 300);
  };

  const handleRetry = (index: number) => {
    setFiles(prev => {
      const newFiles = [...prev];
      newFiles[index].status = 'pending';
      newFiles[index].progress = 0;
      newFiles[index].error = undefined;
      return newFiles;
    });
    simulateUpload(index);
  };

  const handleRemove = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const stats = {
    total: files.length,
    pending: files.filter(f => f.status === 'pending').length,
    uploading: files.filter(f => f.status === 'uploading').length,
    success: files.filter(f => f.status === 'success').length,
    error: files.filter(f => f.status === 'error').length,
  };

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-center space-x-2 mb-4">
        <Upload className="w-5 h-5 text-primary-600 dark:text-primary-400" />
        <div>
          <h3 className="font-bold text-gray-900 dark:text-dark-text-primary">
            Upload de Mãos
          </h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-0.5">
            Envie arquivos de histórico de mãos para análise
          </p>
        </div>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all
          ${isDragging
            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-primary-400 dark:hover:border-primary-500'
          }
        `}
      >
        <Upload className={`w-12 h-12 mx-auto mb-4 ${
          isDragging ? 'text-primary-600 dark:text-primary-400' : 'text-gray-400'
        }`} />
        <p className="text-lg font-medium text-gray-900 dark:text-dark-text-primary mb-2">
          {isDragging ? 'Solte os arquivos aqui' : 'Arraste arquivos aqui'}
        </p>
        <p className="text-sm text-gray-600 dark:text-dark-text-secondary mb-4">
          ou clique para selecionar
        </p>
        <p className="text-xs text-gray-500 dark:text-dark-text-tertiary">
          Formatos suportados: XML (iPoker), TXT/HH (PokerStars), ZIP
        </p>

        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".xml,.txt,.hh,.zip"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Stats */}
      {files.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-4">
          <div className="bg-gray-100 dark:bg-dark-bg-tertiary rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary">
              {stats.total}
            </p>
            <p className="text-xs text-gray-600 dark:text-dark-text-secondary">Total</p>
          </div>
          <div className="bg-blue-100 dark:bg-blue-900/20 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
              {stats.uploading}
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-400">Enviando</p>
          </div>
          <div className="bg-green-100 dark:bg-green-900/20 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-green-600 dark:text-green-400">
              {stats.success}
            </p>
            <p className="text-xs text-green-600 dark:text-green-400">Sucesso</p>
          </div>
          <div className="bg-red-100 dark:bg-red-900/20 rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {stats.error}
            </p>
            <p className="text-xs text-red-600 dark:text-red-400">Erro</p>
          </div>
          <div className="bg-gray-100 dark:bg-dark-bg-tertiary rounded-lg p-3 text-center">
            <p className="text-2xl font-bold text-gray-600 dark:text-gray-400">
              {stats.pending}
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">Pendente</p>
          </div>
        </div>
      )}

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2 max-h-96 overflow-y-auto">
          <h4 className="font-semibold text-gray-900 dark:text-dark-text-primary mb-2">
            Arquivos ({files.length})
          </h4>
          {files.map((file, index) => (
            <div
              key={index}
              className="bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg p-3 flex items-center justify-between"
            >
              <div className="flex items-center space-x-3 flex-1">
                <File className="w-5 h-5 text-gray-400 dark:text-gray-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-dark-text-primary truncate">
                    {file.name}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {formatFileSize(file.size)}
                  </p>

                  {/* Progress Bar */}
                  {file.status === 'uploading' && (
                    <div className="mt-2">
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                        <div
                          className="bg-primary-600 dark:bg-primary-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${file.progress}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {Math.round(file.progress || 0)}%
                      </p>
                    </div>
                  )}

                  {/* Error Message */}
                  {file.status === 'error' && file.error && (
                    <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                      {file.error}
                    </p>
                  )}
                </div>
              </div>

              {/* Status Icon */}
              <div className="flex items-center space-x-2 ml-4">
                {file.status === 'pending' && (
                  <AlertCircle className="w-5 h-5 text-gray-400" />
                )}
                {file.status === 'uploading' && (
                  <Loader2 className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin" />
                )}
                {file.status === 'success' && (
                  <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                )}
                {file.status === 'error' && (
                  <>
                    <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRetry(index);
                      }}
                      className="text-xs text-primary-600 dark:text-primary-400 hover:underline"
                    >
                      Tentar novamente
                    </button>
                  </>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemove(index);
                  }}
                  className="text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                  title="Remover"
                >
                  <XCircle className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Info */}
      <div className="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
        <div className="flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-blue-800 dark:text-blue-300">
            <p className="font-medium mb-1">Como funciona:</p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Arquivos são processados e indexados automaticamente</li>
              <li>Suporta múltiplos formatos: XML (iPoker), TXT/HH (PokerStars), ZIP</li>
              <li>Após o upload, as mãos estarão disponíveis para análise</li>
              <li>O processamento pode levar alguns minutos dependendo do tamanho</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
