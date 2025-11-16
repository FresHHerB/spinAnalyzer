import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Users, TrendingUp, BarChart2, Loader2 } from 'lucide-react';
import { getVillains } from '@/services/api';
import VillainCard from '@/components/VillainCard';
import DataDirectoryConfig from '@/components/DataDirectoryConfig';
import QuickPatternLookup from '@/components/QuickPatternLookup';
import HandUploader from '@/components/HandUploader';

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['villains'],
    queryFn: getVillains,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600 dark:text-primary-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
        <p className="text-red-800 dark:text-red-300">Error loading villains: {(error as Error).message}</p>
      </div>
    );
  }

  const villains = data?.villains || [];
  const totalDecisionPoints = villains.reduce((sum, v) => sum + v.total_decision_points, 0);
  const totalVectors = villains.reduce((sum, v) => sum + v.indexed_vectors, 0);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-dark-text-primary">Dashboard</h2>
        <p className="text-gray-600 dark:text-dark-text-secondary mt-2">
          Pattern matching engine for poker decision analysis
        </p>
      </div>

      {/* Data Directory Config */}
      <DataDirectoryConfig />

      {/* Hand Uploader */}
      <HandUploader />

      {/* Quick Pattern Lookup */}
      <QuickPatternLookup />

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary">Total Villains</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">
                {data?.total_villains || 0}
              </p>
            </div>
            <Users className="w-12 h-12 text-primary-600 dark:text-primary-400 opacity-20 dark:opacity-30" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary">Decision Points</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">{totalDecisionPoints}</p>
            </div>
            <TrendingUp className="w-12 h-12 text-green-600 dark:text-green-400 opacity-20 dark:opacity-30" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600 dark:text-dark-text-secondary">Indexed Vectors</p>
              <p className="text-3xl font-bold text-gray-900 dark:text-dark-text-primary mt-1">{totalVectors}</p>
            </div>
            <BarChart2 className="w-12 h-12 text-blue-600 dark:text-blue-400 opacity-20 dark:opacity-30" />
          </div>
        </div>
      </div>

      {/* Villains Grid */}
      <div>
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-bold text-gray-900 dark:text-dark-text-primary">Villains</h3>
          <Link to="/search" className="btn btn-primary">
            Search Patterns
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {villains.map((villain) => (
            <VillainCard key={villain.name} villain={villain} />
          ))}
        </div>
      </div>
    </div>
  );
}
