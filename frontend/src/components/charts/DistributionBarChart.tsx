import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useTheme } from '@/contexts/ThemeContext';

interface DistributionBarChartProps {
  data: Record<string, number>;
  title: string;
  color?: string;
}

const COLORS = [
  '#0ea5e9', // blue
  '#10b981', // green
  '#f59e0b', // yellow
  '#ef4444', // red
];

export default function DistributionBarChart({ data, title: _title, color: _color = '#0ea5e9' }: DistributionBarChartProps) {
  const { theme } = useTheme();

  const chartData = Object.entries(data).map(([name, value]) => ({
    name,
    value,
  }));

  const total = chartData.reduce((sum, d) => sum + d.value, 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const percentage = ((payload[0].value / total) * 100).toFixed(1);
      return (
        <div className="bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3">
          <p className="font-semibold text-gray-900 dark:text-dark-text-primary capitalize">
            {payload[0].payload.name}
          </p>
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

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={theme === 'dark' ? '#374151' : '#e5e7eb'}
        />
        <XAxis
          dataKey="name"
          stroke={theme === 'dark' ? '#9ca3af' : '#6b7280'}
          tick={{ fill: theme === 'dark' ? '#9ca3af' : '#6b7280' }}
        />
        <YAxis
          stroke={theme === 'dark' ? '#9ca3af' : '#6b7280'}
          tick={{ fill: theme === 'dark' ? '#9ca3af' : '#6b7280' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="value" radius={[8, 8, 0, 0]}>
          {chartData.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
