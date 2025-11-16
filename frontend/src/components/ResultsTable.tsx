import type { DecisionPoint } from '@/types';

interface ResultsTableProps {
  results: DecisionPoint[];
}

export default function ResultsTable({ results }: ResultsTableProps) {
  return (
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
              SPR
            </th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-dark-text-tertiary uppercase tracking-wider">
              Bet Size
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-dark-bg-secondary divide-y divide-gray-200 dark:divide-gray-700">
          {results.map((result) => (
            <tr key={result.decision_id} className="hover:bg-gray-50 dark:hover:bg-dark-bg-tertiary transition-colors">
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
              <td className="px-4 py-3 text-sm text-gray-900 dark:text-dark-text-primary">
                {result.spr?.toFixed(2) || '-'}
              </td>
              <td className="px-4 py-3 text-sm text-gray-900 dark:text-dark-text-primary">
                {result.villain_bet_size_bb
                  ? `${result.villain_bet_size_bb.toFixed(2)} BB`
                  : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
