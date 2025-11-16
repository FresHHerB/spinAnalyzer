import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Loader2, TrendingUp, MapPin, Activity } from 'lucide-react';
import { getVillainStats } from '@/services/api';
import ActionDistributionChart from '@/components/charts/ActionDistributionChart';
import DistributionBarChart from '@/components/charts/DistributionBarChart';
import ExportMenu, { FileText, FileJson, Copy, type ExportOption } from '@/components/ExportMenu';
import { exportVillainStatsToCSV, exportVillainStatsToJSON, copyToClipboard } from '@/utils/export';

export default function VillainProfile() {
  const { villainName } = useParams<{ villainName: string }>();

  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['villain-stats', villainName],
    queryFn: () => getVillainStats(villainName!),
    enabled: !!villainName,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600 dark:text-primary-400" />
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-300">Error loading villain stats</p>
      </div>
    );
  }

  const { villain } = stats;

  const exportOptions: ExportOption[] = [
    {
      label: 'Export as CSV',
      icon: FileText,
      onClick: () => exportVillainStatsToCSV(stats),
    },
    {
      label: 'Export as JSON',
      icon: FileJson,
      onClick: () => exportVillainStatsToJSON(stats),
    },
    {
      label: 'Copy to Clipboard',
      icon: Copy,
      onClick: () => copyToClipboard(stats),
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="card">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-dark-text-primary">{villain.name}</h2>
          <ExportMenu options={exportOptions} label="Export Stats" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <div>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">Decision Points</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">
              {villain.total_decision_points}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">Indexed Vectors</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">
              {villain.indexed_vectors}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">Avg Pot Size</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">
              {villain.avg_pot_bb.toFixed(2)} BB
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">Avg SPR</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">
              {villain.avg_spr?.toFixed(2) || 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Action Distribution Chart */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">
          Action Distribution
        </h3>
        <ActionDistributionChart data={villain.top_actions} />
      </div>

      {/* Streets Distribution */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">Street Distribution</h3>
        <DistributionBarChart data={villain.streets} title="Street Distribution" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {Object.entries(villain.streets).map(([street, count]) => (
            <div key={street} className="text-center p-4 bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg border border-gray-100 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary capitalize">{street}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">{count}</p>
              <p className="text-xs text-gray-500 dark:text-dark-text-tertiary mt-1">
                {((count / villain.total_decision_points) * 100).toFixed(1)}%
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Positions */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">Position Distribution</h3>
        <DistributionBarChart data={villain.positions} title="Position Distribution" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
          {Object.entries(villain.positions).map(([pos, count]) => (
            <div key={pos} className="text-center p-4 bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg border border-gray-100 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary">{pos}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">{count}</p>
              <p className="text-xs text-gray-500 dark:text-dark-text-tertiary mt-1">
                {((count / villain.total_decision_points) * 100).toFixed(1)}%
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Top Actions */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">Top Actions</h3>
        <div className="space-y-3">
          {Object.entries(villain.top_actions).map(([action, count]) => (
            <div key={action} className="flex items-center justify-between">
              <span className="font-medium text-gray-900 dark:text-dark-text-primary">{action}</span>
              <div className="flex items-center space-x-4">
                <div className="w-48 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-primary-600 dark:bg-primary-500 h-2 rounded-full transition-all duration-200"
                    style={{
                      width: `${(count / villain.total_decision_points) * 100}%`,
                    }}
                  />
                </div>
                <span className="text-sm text-gray-600 dark:text-dark-text-secondary w-12 text-right">{count}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pot Size Distribution */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">Pot Size Distribution</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Object.entries(stats.pot_size_distribution).map(([range, count]) => (
            <div key={range} className="text-center p-4 bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg border border-gray-100 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary">{range}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">{count}</p>
            </div>
          ))}
        </div>
      </div>

      {/* SPR Distribution */}
      <div className="card">
        <h3 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">SPR Distribution</h3>
        <div className="grid grid-cols-3 gap-4">
          {Object.entries(stats.spr_distribution).map(([range, count]) => (
            <div key={range} className="text-center p-4 bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg border border-gray-100 dark:border-gray-700">
              <p className="text-sm text-gray-600 dark:text-dark-text-secondary">{range}</p>
              <p className="text-2xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">{count}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
