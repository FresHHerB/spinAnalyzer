import React, { useState, useCallback } from 'react';
import { Upload, X, Check, AlertCircle, Loader2 } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface UploadJob {
  job_id: string;
  filename: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  stage?: string;
  error?: string;
  created_at?: string;
  completed_at?: string;
  parser_stats?: {
    total_files: number;
    total_hands: number;
    hu_hands: number;
    converted: number;
    errors: number;
  };
}

interface FileWithPreview extends File {
  preview?: string;
}

export default function FileUpload() {
  const [files, setFiles] = useState<FileWithPreview[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [jobs, setJobs] = useState<UploadJob[]>([]);
  const [headsUpOnly, setHeadsUpOnly] = useState(true);

  // Handle drag events
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  // Handle drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = Array.from(e.dataTransfer.files).filter((file) =>
      file.name.endsWith('.txt') || file.name.endsWith('.xml')
    );

    if (droppedFiles.length > 0) {
      setFiles((prev) => [...prev, ...droppedFiles]);
    }
  }, []);

  // Handle file input change
  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files).filter((file) =>
        file.name.endsWith('.txt') || file.name.endsWith('.xml')
      );
      setFiles((prev) => [...prev, ...selectedFiles]);
    }
  };

  // Remove file
  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Upload files
  const uploadFiles = async () => {
    if (files.length === 0) return;

    setUploading(true);

    try {
      const uploadPromises = files.map(async (file) => {
        const formData = new FormData();
        formData.append('file', file);

        const response = await axios.post(
          `${API_URL}/upload/file?heads_up_only=${headsUpOnly}`,
          formData,
          {
            headers: { 'Content-Type': 'multipart/form-data' },
          }
        );

        return response.data;
      });

      const results = await Promise.all(uploadPromises);

      setJobs((prev) => [...results, ...prev]);
      setFiles([]);

      // Start polling for job status
      results.forEach((job) => {
        pollJobStatus(job.job_id);
      });
    } catch (error) {
      console.error('Upload error:', error);
      alert('Erro ao fazer upload dos arquivos');
    } finally {
      setUploading(false);
    }
  };

  // Poll job status
  const pollJobStatus = async (jobId: string) => {
    const maxAttempts = 60; // 5 minutes (60 * 5 seconds)
    let attempts = 0;

    const poll = setInterval(async () => {
      try {
        const response = await axios.get(`${API_URL}/upload/status/${jobId}`);
        const job: UploadJob = response.data;

        setJobs((prev) =>
          prev.map((j) => (j.job_id === jobId ? job : j))
        );

        if (job.status === 'completed' || job.status === 'failed') {
          clearInterval(poll);
        }

        attempts++;
        if (attempts >= maxAttempts) {
          clearInterval(poll);
        }
      } catch (error) {
        console.error('Error polling job status:', error);
        clearInterval(poll);
      }
    }, 5000); // Poll every 5 seconds
  };

  // Get status icon
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'queued':
        return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'processing':
        return <Loader2 className="w-5 h-5 text-yellow-500 animate-spin" />;
      case 'completed':
        return <Check className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  // Get status color
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'queued':
        return 'bg-blue-100 text-blue-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white rounded-lg shadow-sm p-6">
        <h2 className="text-2xl font-bold mb-4">Upload Hand Histories</h2>

        {/* Drag and Drop Area */}
        <div
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragActive
              ? 'border-blue-500 bg-blue-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
          <p className="text-lg font-medium mb-2">
            Arraste arquivos aqui ou clique para selecionar
          </p>
          <p className="text-sm text-gray-500 mb-4">
            Aceito: .txt (PokerStars) ou .xml (iPoker)
          </p>
          <input
            type="file"
            multiple
            accept=".txt,.xml"
            onChange={handleFileInput}
            className="hidden"
            id="file-input"
          />
          <label
            htmlFor="file-input"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 transition-colors"
          >
            Selecionar Arquivos
          </label>
        </div>

        {/* Options */}
        <div className="mt-4">
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={headsUpOnly}
              onChange={(e) => setHeadsUpOnly(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <span className="text-sm text-gray-700">
              Processar apenas mãos heads-up
            </span>
          </label>
        </div>

        {/* Selected Files */}
        {files.length > 0 && (
          <div className="mt-6">
            <h3 className="font-medium mb-3">
              Arquivos selecionados ({files.length})
            </h3>
            <div className="space-y-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      {file.name.endsWith('.xml') ? (
                        <div className="w-8 h-8 bg-orange-100 rounded flex items-center justify-center text-orange-600 font-mono text-xs">
                          XML
                        </div>
                      ) : (
                        <div className="w-8 h-8 bg-blue-100 rounded flex items-center justify-center text-blue-600 font-mono text-xs">
                          TXT
                        </div>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024).toFixed(2)} KB
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => removeFile(index)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                  >
                    <X className="w-5 h-5 text-gray-500" />
                  </button>
                </div>
              ))}
            </div>
            <button
              onClick={uploadFiles}
              disabled={uploading}
              className="mt-4 w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {uploading ? 'Enviando...' : `Enviar ${files.length} arquivo(s)`}
            </button>
          </div>
        )}
      </div>

      {/* Jobs List */}
      {jobs.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm p-6">
          <h3 className="text-xl font-bold mb-4">
            Processamento ({jobs.length})
          </h3>
          <div className="space-y-3">
            {jobs.map((job) => (
              <div
                key={job.job_id}
                className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <div className="flex-shrink-0 mt-1">
                      {getStatusIcon(job.status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <p className="text-sm font-medium truncate">
                          {job.filename}
                        </p>
                        <span
                          className={`px-2 py-0.5 text-xs rounded-full ${getStatusColor(
                            job.status
                          )}`}
                        >
                          {job.status}
                        </span>
                      </div>
                      {job.stage && job.status === 'processing' && (
                        <p className="text-xs text-gray-500 mb-2">
                          {job.stage}
                        </p>
                      )}
                      {job.error && (
                        <p className="text-xs text-red-600 mb-2">
                          {job.error}
                        </p>
                      )}
                      {job.parser_stats && job.status === 'completed' && (
                        <div className="mt-2 text-xs text-gray-600 space-y-1">
                          <p>Total de mãos: {job.parser_stats.total_hands}</p>
                          <p>Mãos HU: {job.parser_stats.hu_hands}</p>
                          <p>Convertidas: {job.parser_stats.converted}</p>
                          {job.parser_stats.errors > 0 && (
                            <p className="text-red-600">
                              Erros: {job.parser_stats.errors}
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
