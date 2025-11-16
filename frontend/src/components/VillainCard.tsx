import { Link } from 'react-router-dom';
import { User, TrendingUp, MapPin, Activity } from 'lucide-react';
import type { VillainInfo } from '@/types';

interface VillainCardProps {
  villain: VillainInfo;
}

export default function VillainCard({ villain }: VillainCardProps) {
  const topActions = Object.entries(villain.top_actions).slice(0, 3);
  const topStreet = Object.entries(villain.streets).sort((a, b) => b[1] - a[1])[0];

  return (
    <Link to={`/villain/${villain.name}`} className="card hover:shadow-xl dark:hover:shadow-black/40 transition-all duration-200">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 bg-primary-100 dark:bg-primary-900/30 rounded-full flex items-center justify-center">
            <User className="w-6 h-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <h3 className="font-bold text-gray-900 dark:text-dark-text-primary">{villain.name}</h3>
            <p className="text-sm text-gray-500 dark:text-dark-text-tertiary">
              {villain.total_decision_points} decision points
            </p>
          </div>
        </div>

        <span className="badge badge-info">{villain.indexed_vectors} indexed</span>
      </div>

      <div className="space-y-3">
        {/* Streets */}
        <div className="flex items-center space-x-2 text-sm">
          <MapPin className="w-4 h-4 text-gray-400 dark:text-gray-500" />
          <span className="text-gray-600 dark:text-dark-text-secondary">
            Most active: <span className="font-medium text-gray-900 dark:text-dark-text-primary">{topStreet[0]}</span> ({topStreet[1]})
          </span>
        </div>

        {/* Avg Pot */}
        <div className="flex items-center space-x-2 text-sm">
          <TrendingUp className="w-4 h-4 text-gray-400 dark:text-gray-500" />
          <span className="text-gray-600 dark:text-dark-text-secondary">
            Avg pot: <span className="font-medium text-gray-900 dark:text-dark-text-primary">{villain.avg_pot_bb.toFixed(2)} BB</span>
          </span>
        </div>

        {/* SPR */}
        {villain.avg_spr && (
          <div className="flex items-center space-x-2 text-sm">
            <Activity className="w-4 h-4 text-gray-400 dark:text-gray-500" />
            <span className="text-gray-600 dark:text-dark-text-secondary">
              Avg SPR: <span className="font-medium text-gray-900 dark:text-dark-text-primary">{villain.avg_spr.toFixed(2)}</span>
            </span>
          </div>
        )}

        {/* Top Actions */}
        <div className="pt-3 border-t border-gray-200 dark:border-gray-700">
          <p className="text-xs text-gray-500 dark:text-dark-text-tertiary mb-2">Top Actions</p>
          <div className="flex flex-wrap gap-1">
            {topActions.map(([action, count]) => (
              <span key={action} className="badge badge-success text-xs">
                {action} ({count})
              </span>
            ))}
          </div>
        </div>
      </div>
    </Link>
  );
}
