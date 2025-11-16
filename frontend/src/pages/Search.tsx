import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Search as SearchIcon, Loader2 } from 'lucide-react';
import { getVillains, searchByContext } from '@/services/api';
import type { ContextSearchRequest, DecisionPoint } from '@/types';
import HandReplayer from '@/components/HandReplayer';
import ExportMenu, { FileText, FileJson, Copy, type ExportOption } from '@/components/ExportMenu';
import { exportDecisionPointsToCSV, exportDecisionPointsToJSON, copyToClipboard } from '@/utils/export';

export default function Search() {
  const [request, setRequest] = useState<ContextSearchRequest>({
    villain_name: '',
    k: 10,
  });
  const [selectedHand, setSelectedHand] = useState<DecisionPoint | null>(null);

  const { data: villainsData } = useQuery({
    queryKey: ['villains'],
    queryFn: getVillains,
  });

  const searchMutation = useMutation({
    mutationFn: searchByContext,
    onSuccess: (data) => {
      // Auto-select first result for Hand Replayer
      if (data.results && data.results.length > 0) {
        setSelectedHand(data.results[0]);
      }
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (request.villain_name) {
      searchMutation.mutate(request);
    }
  };

  const results = searchMutation.data?.results || [];

  const exportOptions: ExportOption[] = [
    {
      label: 'Export as CSV',
      icon: FileText,
      onClick: () => exportDecisionPointsToCSV(results),
    },
    {
      label: 'Export as JSON',
      icon: FileJson,
      onClick: () => exportDecisionPointsToJSON(results),
    },
    {
      label: 'Copy to Clipboard',
      icon: Copy,
      onClick: () => copyToClipboard(results),
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-dark-text-primary">Pattern Search</h2>
        <p className="text-gray-600 dark:text-dark-text-secondary mt-2">
          Find similar decision points based on context filters
        </p>
      </div>

      {/* Search Form */}
      <form onSubmit={handleSearch} className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">Query Builder</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Villain */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
              Villain *
            </label>
            <select
              value={request.villain_name}
              onChange={(e) => setRequest({ ...request, villain_name: e.target.value })}
              className="select"
              required
            >
              <option value="">Select villain...</option>
              {villainsData?.villains.map((v) => (
                <option key={v.name} value={v.name}>
                  {v.name} ({v.total_decision_points} DPs)
                </option>
              ))}
            </select>
          </div>

          {/* Street */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-1">Street</label>
            <select
              value={request.street || ''}
              onChange={(e) =>
                setRequest({ ...request, street: e.target.value as any || undefined })
              }
              className="select"
            >
              <option value="">Any</option>
              <option value="preflop">Preflop</option>
              <option value="flop">Flop</option>
              <option value="turn">Turn</option>
              <option value="river">River</option>
            </select>
          </div>

          {/* Position */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-1">Position</label>
            <select
              value={request.position || ''}
              onChange={(e) =>
                setRequest({ ...request, position: e.target.value as any || undefined })
              }
              className="select"
            >
              <option value="">Any</option>
              <option value="BTN">BTN</option>
              <option value="BB">BB</option>
              <option value="IP">IP</option>
              <option value="OOP">OOP</option>
            </select>
          </div>

          {/* Pot BB Min */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
              Min Pot (BB)
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 5.0"
              value={request.pot_bb_min || ''}
              onChange={(e) =>
                setRequest({
                  ...request,
                  pot_bb_min: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="input"
            />
          </div>

          {/* Pot BB Max */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
              Max Pot (BB)
            </label>
            <input
              type="number"
              step="0.1"
              placeholder="e.g. 20.0"
              value={request.pot_bb_max || ''}
              onChange={(e) =>
                setRequest({
                  ...request,
                  pot_bb_max: e.target.value ? parseFloat(e.target.value) : undefined,
                })
              }
              className="input"
            />
          </div>

          {/* Results Count */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-dark-text-secondary mb-1">
              Results (k)
            </label>
            <input
              type="number"
              min="1"
              max="100"
              value={request.k || 10}
              onChange={(e) =>
                setRequest({ ...request, k: parseInt(e.target.value) || 10 })
              }
              className="input"
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end">
          <button
            type="submit"
            disabled={searchMutation.isPending || !request.villain_name}
            className="btn btn-primary flex items-center space-x-2"
          >
            {searchMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <SearchIcon className="w-4 h-4" />
            )}
            <span>Search</span>
          </button>
        </div>
      </form>

      {/* Hand Replayer */}
      {selectedHand && (
        <HandReplayer hand={selectedHand} />
      )}

      {/* Results */}
      {searchMutation.data && (
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary">
                Results ({searchMutation.data.total_results})
              </h3>
              <span className="text-sm text-gray-500 dark:text-dark-text-tertiary">
                Search time: {searchMutation.data.search_time_ms.toFixed(2)}ms
              </span>
            </div>
            {results.length > 0 && <ExportMenu options={exportOptions} />}
          </div>

          {results.length > 0 ? (
            <div>
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary mb-3">
                Click a row to view in Hand Replayer
              </p>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-dark-bg-tertiary">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
                        Decision ID
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
                        Street
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
                        Position
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
                        Action
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
                        Pot (BB)
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
                        Distance
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-dark-bg-secondary divide-y divide-gray-200 dark:divide-gray-700">
                    {results.map((result) => (
                      <tr
                        key={result.decision_id}
                        onClick={() => setSelectedHand(result)}
                        className={`cursor-pointer transition-colors ${
                          selectedHand?.decision_id === result.decision_id
                            ? 'bg-primary-50 dark:bg-primary-900/30'
                            : 'hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary'
                        }`}
                      >
                        <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-dark-text-primary">
                          {result.decision_id}
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="badge badge-info">{result.street}</span>
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <span className="badge badge-success">{result.villain_position}</span>
                        </td>
                        <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-dark-text-primary">
                          {result.villain_action}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-900 dark:text-dark-text-primary">
                          {result.pot_bb.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-dark-text-secondary">
                          {result.distance?.toFixed(4) || 'N/A'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="text-gray-500 dark:text-dark-text-tertiary text-center py-8">No results found</p>
          )}
        </div>
      )}

      {searchMutation.error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-300">
            Search error: {(searchMutation.error as Error).message}
          </p>
        </div>
      )}
    </div>
  );
}
