import { useState, useEffect } from 'react';
import { Bookmark, Trash2, Play, Edit2, Download, Upload, Search, Clock, TrendingUp } from 'lucide-react';
import type { SavedQuery } from '@/utils/savedQueries';
import {
  loadSavedQueries,
  deleteQuery,
  markQueryUsed,
  getQueryStats,
  exportQueries,
  importQueries,
  searchQueries,
} from '@/utils/savedQueries';

interface SavedQueriesManagerProps {
  onLoadQuery?: (query: SavedQuery) => void;
  compact?: boolean;
}

export default function SavedQueriesManager({ onLoadQuery, compact = false }: SavedQueriesManagerProps) {
  const [queries, setQueries] = useState<SavedQuery[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState(getQueryStats());

  useEffect(() => {
    loadQueries();
  }, []);

  const loadQueries = () => {
    const loaded = searchTerm ? searchQueries(searchTerm) : loadSavedQueries();
    setQueries(loaded);
    setStats(getQueryStats());
  };

  const handleDelete = (id: string) => {
    if (confirm('Tem certeza que deseja deletar esta query salva?')) {
      deleteQuery(id);
      loadQueries();
    }
  };

  const handleLoad = (query: SavedQuery) => {
    markQueryUsed(query.id);
    loadQueries();
    onLoadQuery?.(query);
  };

  const handleExport = () => {
    const json = exportQueries();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `spinanalyzer-queries-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        if (importQueries(content, 'merge')) {
          loadQueries();
          alert('Queries importadas com sucesso!');
        } else {
          alert('Erro ao importar queries. Verifique o formato do arquivo.');
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'agora';
    if (diffMins < 60) return `${diffMins}min atrás`;
    if (diffHours < 24) return `${diffHours}h atrás`;
    if (diffDays < 7) return `${diffDays}d atrás`;
    return date.toLocaleDateString('pt-BR');
  };

  const getQuerySummary = (query: SavedQuery) => {
    const parts = [];
    if (query.street) parts.push(query.street);
    if (query.position) parts.push(query.position);
    if (query.action) parts.push(query.action);
    if (query.pot_bb_min || query.pot_bb_max) {
      parts.push(`Pot: ${query.pot_bb_min || '0'}-${query.pot_bb_max || '∞'} BB`);
    }
    return parts.length > 0 ? parts.join(', ') : 'Qualquer situação';
  };

  if (compact) {
    return (
      <div className="space-y-2">
        {queries.slice(0, 5).map((query) => (
          <button
            key={query.id}
            onClick={() => handleLoad(query)}
            className="w-full text-left px-3 py-2 bg-gray-50 dark:bg-dark-bg-tertiary hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <p className="font-medium text-sm text-gray-900 dark:text-dark-text-primary">
                  {query.name}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {query.villain_name} • {getQuerySummary(query)}
                </p>
              </div>
              {query.use_count > 0 && (
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {query.use_count}x
                </span>
              )}
            </div>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Bookmark className="w-5 h-5 text-primary-600 dark:text-primary-400" />
          <div>
            <h3 className="font-bold text-gray-900 dark:text-dark-text-primary">
              Queries Salvas
            </h3>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-0.5">
              {stats.total} queries • {stats.totalUses} usos totais
            </p>
          </div>
        </div>

        <div className="flex space-x-2">
          <button
            onClick={handleImport}
            className="btn btn-secondary text-sm flex items-center space-x-1"
            title="Importar queries"
          >
            <Upload className="w-4 h-4" />
            <span>Importar</span>
          </button>
          <button
            onClick={handleExport}
            disabled={queries.length === 0}
            className="btn btn-secondary text-sm flex items-center space-x-1"
            title="Exportar queries"
          >
            <Download className="w-4 h-4" />
            <span>Exportar</span>
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar queries..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              loadQueries();
            }}
            className="input pl-10 text-sm"
          />
        </div>
      </div>

      {/* Stats Bar */}
      {stats.mostUsed && (
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
            <div className="flex items-center space-x-2 mb-1">
              <TrendingUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-xs font-medium text-blue-800 dark:text-blue-300">
                Mais Usada
              </span>
            </div>
            <p className="text-sm font-semibold text-blue-900 dark:text-blue-200 truncate">
              {stats.mostUsed.name}
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-400">
              {stats.mostUsed.use_count} usos
            </p>
          </div>

          {stats.recentlyUsed && (
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
              <div className="flex items-center space-x-2 mb-1">
                <Clock className="w-4 h-4 text-green-600 dark:text-green-400" />
                <span className="text-xs font-medium text-green-800 dark:text-green-300">
                  Recente
                </span>
              </div>
              <p className="text-sm font-semibold text-green-900 dark:text-green-200 truncate">
                {stats.recentlyUsed.name}
              </p>
              <p className="text-xs text-green-600 dark:text-green-400">
                {formatDate(stats.recentlyUsed.last_used!)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Queries List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {queries.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <Bookmark className="w-12 h-12 mx-auto mb-2 opacity-30" />
            <p className="text-sm">
              {searchTerm ? 'Nenhuma query encontrada' : 'Nenhuma query salva ainda'}
            </p>
            <p className="text-xs mt-1">
              {!searchTerm && 'Salve suas buscas favoritas para reutilizá-las rapidamente'}
            </p>
          </div>
        ) : (
          queries.map((query) => (
            <div
              key={query.id}
              className="bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg p-4 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <h4 className="font-semibold text-gray-900 dark:text-dark-text-primary">
                    {query.name}
                  </h4>
                  {query.description && (
                    <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
                      {query.description}
                    </p>
                  )}
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  <button
                    onClick={() => handleLoad(query)}
                    className="p-2 hover:bg-primary-100 dark:hover:bg-primary-900/30 rounded-lg transition-colors"
                    title="Carregar query"
                  >
                    <Play className="w-4 h-4 text-primary-600 dark:text-primary-400" />
                  </button>
                  <button
                    onClick={() => handleDelete(query.id)}
                    className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                    title="Deletar query"
                  >
                    <Trash2 className="w-4 h-4 text-red-600 dark:text-red-400" />
                  </button>
                </div>
              </div>

              <div className="space-y-1 text-sm">
                <div className="flex items-center space-x-2">
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    Jogador:
                  </span>
                  <span className="text-gray-900 dark:text-dark-text-primary font-semibold">
                    {query.villain_name}
                  </span>
                </div>
                <div className="text-gray-600 dark:text-dark-text-secondary">
                  {getQuerySummary(query)}
                </div>
              </div>

              <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
                <div className="flex items-center space-x-4 text-xs text-gray-500 dark:text-gray-400">
                  <span>Criada: {formatDate(query.created_at)}</span>
                  {query.last_used && <span>Último uso: {formatDate(query.last_used)}</span>}
                </div>
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  {query.use_count} {query.use_count === 1 ? 'uso' : 'usos'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
