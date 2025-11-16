import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Search, TrendingUp, Loader2, Info, Bookmark, Save, FolderOpen } from 'lucide-react';
import { getVillains, searchByContext, analyzeRange } from '@/services/api';
import type { ContextSearchRequest, RangeAnalysisRequest } from '@/types';
import type { SavedQuery } from '@/utils/savedQueries';
import { saveQuery, loadSavedQueries } from '@/utils/savedQueries';
import RangeAnalysisDisplay from './RangeAnalysisDisplay';
import SavedQueriesManager from './SavedQueriesManager';

export default function QuickPatternLookup() {
  const [villain, setVillain] = useState('');
  const [street, setStreet] = useState<string>('');
  const [position, setPosition] = useState<string>('');
  const [potMin, setPotMin] = useState<number | undefined>();
  const [potMax, setPotMax] = useState<number | undefined>();
  const [action, setAction] = useState<string>('');

  // Saved queries state
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [showSavedQueries, setShowSavedQueries] = useState(false);
  const [queryName, setQueryName] = useState('');
  const [queryDescription, setQueryDescription] = useState('');

  const { data: villainsData } = useQuery({
    queryKey: ['villains'],
    queryFn: getVillains,
  });

  const searchMutation = useMutation({
    mutationFn: searchByContext,
  });

  const rangeAnalysisMutation = useMutation({
    mutationFn: analyzeRange,
  });

  const handleAnalyze = () => {
    if (!villain) return;

    const contextRequest: ContextSearchRequest = {
      villain_name: villain,
      street: street || undefined,
      position: position || undefined,
      pot_bb_min: potMin,
      pot_bb_max: potMax,
      k: 50, // Get more results for pattern analysis
    };

    const rangeRequest: RangeAnalysisRequest = {
      villain_name: villain,
      street: street || undefined,
      position: position || undefined,
      action: action || undefined,
      pot_bb_min: potMin,
      pot_bb_max: potMax,
    };

    // Run both analyses
    searchMutation.mutate(contextRequest);
    rangeAnalysisMutation.mutate(rangeRequest);
  };

  const handleSaveQuery = () => {
    if (!queryName.trim() || !villain) return;

    saveQuery({
      name: queryName.trim(),
      description: queryDescription.trim() || undefined,
      villain_name: villain,
      street: street || undefined,
      position: position || undefined,
      action: action || undefined,
      pot_bb_min: potMin,
      pot_bb_max: potMax,
    });

    setQueryName('');
    setQueryDescription('');
    setShowSaveDialog(false);
    alert('Query salva com sucesso!');
  };

  const handleLoadQuery = (query: SavedQuery) => {
    setVillain(query.villain_name);
    setStreet(query.street || '');
    setPosition(query.position || '');
    setAction(query.action || '');
    setPotMin(query.pot_bb_min);
    setPotMax(query.pot_bb_max);
    setShowSavedQueries(false);

    // Auto-execute the query
    setTimeout(() => {
      const contextRequest: ContextSearchRequest = {
        villain_name: query.villain_name,
        street: query.street || undefined,
        position: query.position || undefined,
        pot_bb_min: query.pot_bb_min,
        pot_bb_max: query.pot_bb_max,
        k: 50,
      };

      const rangeRequest: RangeAnalysisRequest = {
        villain_name: query.villain_name,
        street: query.street || undefined,
        position: query.position || undefined,
        action: query.action || undefined,
        pot_bb_min: query.pot_bb_min,
        pot_bb_max: query.pot_bb_max,
      };

      searchMutation.mutate(contextRequest);
      rangeAnalysisMutation.mutate(rangeRequest);
    }, 100);
  };

  // Analyze patterns from results
  const patterns = searchMutation.data?.results.reduce((acc, result) => {
    const action = result.villain_action;
    acc[action] = (acc[action] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const totalResults = searchMutation.data?.total_results || 0;
  const sortedActions = patterns
    ? Object.entries(patterns)
        .sort(([, a], [, b]) => b - a)
        .slice(0, 5)
    : [];

  const getMostCommonAction = () => {
    if (!sortedActions.length) return null;
    const [action, count] = sortedActions[0];
    const percentage = ((count / totalResults) * 100).toFixed(1);
    return { action, count, percentage };
  };

  const mostCommon = getMostCommonAction();

  return (
    <div className="card">
      <div className="flex items-start space-x-3 mb-4">
        <Search className="w-5 h-5 text-primary-600 dark:text-primary-400 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-bold text-gray-900 dark:text-dark-text-primary">
            Análise Rápida de Padrões
          </h3>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
            Veja diretamente o que um jogador faz em situações específicas
          </p>
        </div>
      </div>

      {/* Query Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
        {/* Villain */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
            Jogador *
          </label>
          <select
            value={villain}
            onChange={(e) => setVillain(e.target.value)}
            className="select text-sm"
          >
            <option value="">Selecione...</option>
            {villainsData?.villains.map((v) => (
              <option key={v.name} value={v.name}>
                {v.name}
              </option>
            ))}
          </select>
        </div>

        {/* Street */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
            Street
          </label>
          <select
            value={street}
            onChange={(e) => setStreet(e.target.value)}
            className="select text-sm"
          >
            <option value="">Qualquer</option>
            <option value="preflop">Preflop</option>
            <option value="flop">Flop</option>
            <option value="turn">Turn</option>
            <option value="river">River</option>
          </select>
        </div>

        {/* Position */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
            Posição
          </label>
          <select
            value={position}
            onChange={(e) => setPosition(e.target.value)}
            className="select text-sm"
          >
            <option value="">Qualquer</option>
            <option value="BTN">BTN</option>
            <option value="BB">BB</option>
            <option value="IP">IP</option>
            <option value="OOP">OOP</option>
          </select>
        </div>

        {/* Action */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
            Ação
          </label>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="select text-sm"
          >
            <option value="">Qualquer</option>
            <option value="bet">Bet</option>
            <option value="raise">Raise</option>
            <option value="call">Call</option>
            <option value="check">Check</option>
            <option value="fold">Fold</option>
          </select>
        </div>

        {/* Pot Min */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
            Pot Min (BB)
          </label>
          <input
            type="number"
            step="0.5"
            placeholder="Ex: 5"
            value={potMin || ''}
            onChange={(e) => setPotMin(e.target.value ? parseFloat(e.target.value) : undefined)}
            className="input text-sm"
          />
        </div>

        {/* Pot Max */}
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
            Pot Max (BB)
          </label>
          <input
            type="number"
            step="0.5"
            placeholder="Ex: 20"
            value={potMax || ''}
            onChange={(e) => setPotMax(e.target.value ? parseFloat(e.target.value) : undefined)}
            className="input text-sm"
          />
        </div>

        {/* Analyze Button */}
        <div className="flex items-end">
          <button
            onClick={handleAnalyze}
            disabled={!villain || searchMutation.isPending || rangeAnalysisMutation.isPending}
            className="btn btn-primary w-full flex items-center justify-center space-x-2 text-sm"
          >
            {(searchMutation.isPending || rangeAnalysisMutation.isPending) ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <TrendingUp className="w-4 h-4" />
            )}
            <span>Analisar Padrão</span>
          </button>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex space-x-2">
          <button
            onClick={() => setShowSavedQueries(!showSavedQueries)}
            className="btn btn-secondary text-sm flex items-center space-x-2"
          >
            <FolderOpen className="w-4 h-4" />
            <span>Carregar Query</span>
          </button>
          <button
            onClick={() => setShowSaveDialog(true)}
            disabled={!villain}
            className="btn btn-secondary text-sm flex items-center space-x-2"
          >
            <Bookmark className="w-4 h-4" />
            <span>Salvar Query</span>
          </button>
        </div>
      </div>

      {/* Save Dialog */}
      {showSaveDialog && (
        <div className="mb-4 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <h4 className="font-semibold text-gray-900 dark:text-dark-text-primary mb-3">
            Salvar Query Atual
          </h4>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
                Nome da Query *
              </label>
              <input
                type="text"
                placeholder="Ex: BahTOBUK Flop BTN Bet"
                value={queryName}
                onChange={(e) => setQueryName(e.target.value)}
                className="input text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
                Descrição (opcional)
              </label>
              <input
                type="text"
                placeholder="Ex: Analisa probe bets no flop em posição"
                value={queryDescription}
                onChange={(e) => setQueryDescription(e.target.value)}
                className="input text-sm"
              />
            </div>
            <div className="flex space-x-2">
              <button
                onClick={handleSaveQuery}
                disabled={!queryName.trim()}
                className="btn btn-primary text-sm flex items-center space-x-1"
              >
                <Save className="w-4 h-4" />
                <span>Salvar</span>
              </button>
              <button
                onClick={() => {
                  setShowSaveDialog(false);
                  setQueryName('');
                  setQueryDescription('');
                }}
                className="btn btn-secondary text-sm"
              >
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Saved Queries Manager */}
      {showSavedQueries && (
        <div className="mb-6">
          <SavedQueriesManager onLoadQuery={handleLoadQuery} />
        </div>
      )}

      {/* Results Summary */}
      {searchMutation.data && (
        <div className="space-y-4">
          {/* Main Result */}
          {mostCommon ? (
            <div className="bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20 border-2 border-primary-200 dark:border-primary-800 rounded-lg p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary mb-1">
                    Ação Mais Comum
                  </p>
                  <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
                    {mostCommon.action}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-dark-text-secondary mt-2">
                    {mostCommon.count} de {totalResults} vezes ({mostCommon.percentage}%)
                  </p>
                </div>
                <div className="text-right">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-primary-100 dark:bg-primary-900/30">
                    <span className="text-2xl font-bold text-primary-600 dark:text-primary-400">
                      {mostCommon.percentage}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center">
              <p className="text-yellow-800 dark:text-yellow-300">
                Nenhum padrão encontrado para esta situação específica
              </p>
            </div>
          )}

          {/* Distribution */}
          {sortedActions.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-900 dark:text-dark-text-primary mb-3">
                Distribuição de Ações
              </h4>
              <div className="space-y-2">
                {sortedActions.map(([action, count]) => {
                  const percentage = ((count / totalResults) * 100).toFixed(1);
                  return (
                    <div key={action} className="flex items-center justify-between">
                      <div className="flex items-center space-x-3 flex-1">
                        <span className="font-medium text-gray-900 dark:text-dark-text-primary min-w-[120px]">
                          {action}
                        </span>
                        <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                          <div
                            className="bg-primary-500 dark:bg-primary-600 h-6 flex items-center justify-end px-2 transition-all duration-300"
                            style={{ width: `${percentage}%` }}
                          >
                            <span className="text-xs font-semibold text-white">
                              {parseFloat(percentage) > 10 ? `${percentage}%` : ''}
                            </span>
                          </div>
                        </div>
                      </div>
                      <span className="text-sm text-gray-600 dark:text-dark-text-secondary ml-4 min-w-[60px] text-right">
                        {count}x ({percentage}%)
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Context Info */}
          <div className="bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg p-3 text-sm">
            <div className="flex items-start space-x-2">
              <Info className="w-4 h-4 text-gray-500 dark:text-gray-400 mt-0.5 flex-shrink-0" />
              <div className="space-y-1 text-gray-600 dark:text-dark-text-secondary">
                <p>
                  <strong>Jogador:</strong> {villain}
                </p>
                <p>
                  <strong>Situação:</strong>{' '}
                  {street || 'Qualquer street'},{' '}
                  {position || 'Qualquer posição'}
                  {potMin || potMax ? `, Pot: ${potMin || '0'}-${potMax || '∞'} BB` : ''}
                </p>
                <p>
                  <strong>Amostras:</strong> {totalResults} decision points encontrados
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                  Busca tempo: {searchMutation.data.search_time_ms.toFixed(2)}ms
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Range Analysis Results */}
      {rangeAnalysisMutation.data && (
        <div className="mt-6 pt-6 border-t-2 border-gray-200 dark:border-gray-700">
          <RangeAnalysisDisplay
            data={rangeAnalysisMutation.data}
            villain={villain}
            context={{
              street: street || undefined,
              position: position || undefined,
              potMin: potMin,
              potMax: potMax,
            }}
          />
        </div>
      )}

      {/* Errors */}
      {searchMutation.error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-sm text-red-800 dark:text-red-300">
            Erro ao buscar padrões: {(searchMutation.error as Error).message}
          </p>
        </div>
      )}
      {rangeAnalysisMutation.error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-sm text-red-800 dark:text-red-300">
            Erro ao analisar holdings: {(rangeAnalysisMutation.error as Error).message}
          </p>
        </div>
      )}
    </div>
  );
}
