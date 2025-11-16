import { useState } from 'react';
import { FolderOpen, Save, AlertCircle } from 'lucide-react';

interface DataDirectoryConfigProps {
  onSave?: (directory: string) => void;
}

export default function DataDirectoryConfig({ onSave }: DataDirectoryConfigProps) {
  const [directory, setDirectory] = useState(() => {
    return localStorage.getItem('spinanalyzer-data-directory') || 'C:\\Users\\faelz\\Desktop\\k\\exported\\PokerStars';
  });
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = () => {
    localStorage.setItem('spinanalyzer-data-directory', directory);
    setIsSaved(true);
    onSave?.(directory);

    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleBrowse = () => {
    // Note: Browser File System Access API would be used here in production
    // For now, users can paste the path
    alert('Cole o caminho completo do diretório com as mãos exportadas do PokerStars');
  };

  return (
    <div className="card">
      <div className="flex items-start space-x-3 mb-4">
        <FolderOpen className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-bold text-gray-900 dark:text-dark-text-primary">
            Diretório de Dados
          </h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
            Configure onde estão localizados os arquivos de mãos exportadas
          </p>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-2">
            Caminho do Diretório
          </label>
          <div className="flex space-x-2">
            <input
              type="text"
              value={directory}
              onChange={(e) => setDirectory(e.target.value)}
              placeholder="C:\Users\faelz\Desktop\k\exported\PokerStars"
              className="input flex-1 font-mono text-sm"
            />
            <button
              onClick={handleBrowse}
              className="btn btn-secondary flex items-center space-x-2"
              title="Selecionar diretório"
            >
              <FolderOpen className="w-4 h-4" />
              <span>Procurar</span>
            </button>
          </div>
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3 flex items-start space-x-2">
          <AlertCircle className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
          <p className="text-sm text-blue-800 dark:text-blue-300">
            <strong>Formatos suportados:</strong> XML (iPoker), TXT/HH (PokerStars), ZIP com múltiplas mãos
          </p>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={!directory.trim()}
            className="btn btn-primary flex items-center space-x-2"
          >
            <Save className="w-4 h-4" />
            <span>{isSaved ? 'Salvo!' : 'Salvar Configuração'}</span>
          </button>
        </div>

        <div className="text-xs text-gray-500 dark:text-dark-text-tertiary">
          <p><strong>Padrão:</strong> C:\Users\faelz\Desktop\k\exported\PokerStars</p>
          <p className="mt-1"><strong>Atual:</strong> {directory || 'Não configurado'}</p>
        </div>
      </div>
    </div>
  );
}
