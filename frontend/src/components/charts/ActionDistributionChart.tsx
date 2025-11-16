import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { useTheme } from '@/contexts/ThemeContext';

interface ActionDistributionChartProps {
  data: Record<string, number>;
}

const COLORS = [
  '#0ea5e9', // primary
  '#10b981', // green
  '#f59e0b', // yellow
  '#ef4444', // red
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
];

export default function ActionDistributionChart({ data }: ActionDistributionChartProps) {
  const { theme } = useTheme();

  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const percentage = ((payload[0].value / chartData.reduce((sum, d) => sum + d.value, 0)) * 100).toFixed(1);
      return (
        <div className="bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="font-semibold text-gray-900 dark:text-dark-text-primary">{payload[0].name}</p>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
            Count: {payload[0].value}
          </p>
          <p className="text-sm text-gray-600 dark:text-dark-text-secondary">
            {percentage}%
          </p>
        </div>
      );
    }
    return null;
  };

  const renderLabel = (entry: any) => {
    const percentage = ((entry.value / chartData.reduce((sum, d) => sum + d.value, 0)) * 100).toFixed(0);
    return `${percentage}%`;
  };

  return (
    <ResponsiveContainer width="100%" height={350}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={renderLabel}
          outerRadius={120}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{
            color: theme === 'dark' ? '#cbd5e1' : '#4b5563',
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
