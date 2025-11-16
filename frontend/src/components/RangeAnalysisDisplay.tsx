import { TrendingUp, AlertCircle, BarChart3 } from 'lucide-react';
import type { RangeAnalysisResponse } from '@/types';

interface RangeAnalysisDisplayProps {
  data: RangeAnalysisResponse;
  villain: string;
  context: {
    street?: string;
    position?: string;
    action?: string;
    potMin?: number;
    potMax?: number;
  };
}

export default function RangeAnalysisDisplay({ data, villain, context }: RangeAnalysisDisplayProps) {
  if (data.total_samples === 0) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 text-center">
        <AlertCircle className="w-6 h-6 text-yellow-600 dark:text-yellow-400 mx-auto mb-2" />
        <p className="text-yellow-800 dark:text-yellow-300">
          Nenhum dado encontrado para esta situação específica
        </p>
      </div>
    );
  }

  // Categorize hands into Value, Draw, Bluff
  const categorizeHoldings = () => {
    const categories = {
      value: 0,
      draw: 0,
      bluff: 0,
    };

    // Strong value hands
    const valueStrengths = ['STRAIGHT_FLUSH', 'FOUR_OF_A_KIND', 'FULL_HOUSE', 'FLUSH', 'STRAIGHT', 'THREE_OF_A_KIND', 'TWO_PAIR'];

    Object.entries(data.hand_strength_distribution).forEach(([strength, dist]) => {
      const strengthUpper = strength.toUpperCase();
      if (valueStrengths.some(v => strengthUpper.includes(v))) {
        categories.value += dist.count;
      } else if (strengthUpper.includes('PAIR') || strengthUpper.includes('ONE_PAIR')) {
        // Check if has draw
        const totalDraws = Object.values(data.draws_distribution).reduce((sum, d) => sum + d.count, 0);
        if (totalDraws > 0) {
          categories.draw += dist.count * 0.5; // Semi-bluff
          categories.value += dist.count * 0.5;
        } else {
          categories.value += dist.count;
        }
      } else {
        categories.bluff += dist.count;
      }
    });

    // Pure draws
    Object.entries(data.draws_distribution).forEach(([_, dist]) => {
      categories.draw += dist.count;
    });

    const total = categories.value + categories.draw + categories.bluff;
    return {
      value: total > 0 ? ((categories.value / total) * 100).toFixed(1) : '0',
      draw: total > 0 ? ((categories.draw / total) * 100).toFixed(1) : '0',
      bluff: total > 0 ? ((categories.bluff / total) * 100).toFixed(1) : '0',
    };
  };

  const rangeCategory = categorizeHoldings();

  return (
    <div className="space-y-6">
      {/* Header Summary */}
      <div className="bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20 border-2 border-primary-200 dark:border-primary-800 rounded-lg p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-xl font-bold text-gray-900 dark:text-dark-text-primary mb-2">
              Análise de Holdings - {villain}
            </h3>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
              <strong>Situação:</strong> {context.street || 'Qualquer street'}, {context.position || 'Qualquer posição'}
              {context.action && <>, Ação: {context.action}</>}
              {(context.potMin || context.potMax) && (
                <>, Pot: {context.potMin || '0'}-{context.potMax || '∞'} BB</>
              )}
            </p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {data.total_samples}
            </p>
            <p className="text-sm text-gray-600 dark:text-dark-text-secondary">amostras</p>
          </div>
        </div>

        {/* Range Categories */}
        <div className="grid grid-cols-3 gap-4 mt-6">
          <div className="bg-white dark:bg-dark-bg-tertiary rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-600 dark:text-green-400">
              {rangeCategory.value}%
            </div>
            <div className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
              Valor
            </div>
          </div>
          <div className="bg-white dark:bg-dark-bg-tertiary rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
              {rangeCategory.draw}%
            </div>
            <div className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
              Draws / Semi-Bluff
            </div>
          </div>
          <div className="bg-white dark:bg-dark-bg-tertiary rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-red-600 dark:text-red-400">
              {rangeCategory.bluff}%
            </div>
            <div className="text-sm text-gray-600 dark:text-dark-text-secondary mt-1">
              Blefe
            </div>
          </div>
        </div>
      </div>

      {/* Hand Strength Distribution */}
      {Object.keys(data.hand_strength_distribution).length > 0 && (
        <div className="card">
          <div className="flex items-center space-x-2 mb-4">
            <BarChart3 className="w-5 h-5 text-primary-600 dark:text-primary-400" />
            <h4 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary">
              Força das Mãos
            </h4>
          </div>
          <div className="space-y-3">
            {Object.entries(data.hand_strength_distribution)
              .sort(([, a], [, b]) => b.percentage - a.percentage)
              .map(([strength, dist]) => (
                <div key={strength} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1">
                    <span className="font-medium text-gray-900 dark:text-dark-text-primary min-w-[150px] text-sm">
                      {strength.replace(/_/g, ' ')}
                    </span>
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                      <div
                        className="bg-green-500 dark:bg-green-600 h-6 flex items-center justify-end px-2 transition-all duration-300"
                        style={{ width: `${Math.min(dist.percentage, 100)}%` }}
                      >
                        {dist.percentage > 10 && (
                          <span className="text-xs font-semibold text-white">
                            {dist.percentage.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span className="text-sm text-gray-600 dark:text-dark-text-secondary ml-4 min-w-[80px] text-right">
                    {dist.count}x ({dist.percentage.toFixed(1)}%)
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Draws Distribution */}
      {Object.keys(data.draws_distribution).length > 0 && (
        <div className="card">
          <div className="flex items-center space-x-2 mb-4">
            <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h4 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary">
              Draws Presentes
            </h4>
          </div>
          <div className="space-y-3">
            {Object.entries(data.draws_distribution)
              .sort(([, a], [, b]) => b.percentage - a.percentage)
              .map(([draw, dist]) => (
                <div key={draw} className="flex items-center justify-between">
                  <div className="flex items-center space-x-3 flex-1">
                    <span className="font-medium text-gray-900 dark:text-dark-text-primary min-w-[150px] text-sm">
                      {draw}
                    </span>
                    <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-6 overflow-hidden">
                      <div
                        className="bg-purple-500 dark:bg-purple-600 h-6 flex items-center justify-end px-2 transition-all duration-300"
                        style={{ width: `${Math.min(dist.percentage, 100)}%` }}
                      >
                        {dist.percentage > 10 && (
                          <span className="text-xs font-semibold text-white">
                            {dist.percentage.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span className="text-sm text-gray-600 dark:text-dark-text-secondary ml-4 min-w-[80px] text-right">
                    {dist.count}x ({dist.percentage.toFixed(1)}%)
                  </span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Examples */}
      {data.examples.length > 0 && (
        <div className="card">
          <h4 className="text-lg font-bold text-gray-900 dark:text-dark-text-primary mb-4">
            Exemplos Reais ({data.examples.length})
          </h4>
          <div className="space-y-3">
            {data.examples.map((example, idx) => (
              <div
                key={idx}
                className="bg-gray-50 dark:bg-dark-bg-tertiary rounded-lg p-4 border border-gray-200 dark:border-gray-700"
              >
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <div>
                    <p className="text-gray-500 dark:text-gray-400 text-xs">Mão</p>
                    <p className="font-mono font-bold text-gray-900 dark:text-dark-text-primary">
                      {example.villain_hand}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500 dark:text-gray-400 text-xs">Força</p>
                    <p className="font-medium text-gray-900 dark:text-dark-text-primary">
                      {example.hand_strength.replace(/_/g, ' ')}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500 dark:text-gray-400 text-xs">Board</p>
                    <p className="font-mono font-medium text-gray-900 dark:text-dark-text-primary">
                      {example.board || 'N/A'}
                    </p>
                  </div>
                  <div>
                    <p className="text-gray-500 dark:text-gray-400 text-xs">Ação</p>
                    <p className="font-medium text-primary-600 dark:text-primary-400">
                      {example.action}
                    </p>
                  </div>
                </div>
                {example.draws && example.draws !== 'None' && example.draws !== '[]' && (
                  <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      Draws: <span className="text-purple-600 dark:text-purple-400 font-medium">{example.draws}</span>
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
        Busca executada em {data.search_time_ms.toFixed(2)}ms
      </div>
    </div>
  );
}
