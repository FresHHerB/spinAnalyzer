import { Link, useLocation } from 'react-router-dom';
import { Home, Search, BarChart3, Github, Upload } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getHealth } from '@/services/api';
import ThemeToggle from './ThemeToggle';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    refetchInterval: 30000, // 30 seconds
  });

  const navItems = [
    { path: '/', label: 'Dashboard', icon: Home },
    { path: '/search', label: 'Search', icon: Search },
    { path: '/upload', label: 'Upload', icon: Upload },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-bg-primary transition-colors duration-200">
      {/* Header */}
      <header className="bg-white dark:bg-dark-bg-secondary shadow-sm sticky top-0 z-50 border-b border-gray-200 dark:border-gray-700 transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <BarChart3 className="w-8 h-8 text-primary-600 dark:text-primary-400" />
                <div>
                  <h1 className="text-xl font-bold text-gray-900 dark:text-dark-text-primary">SpinAnalyzer</h1>
                  <p className="text-xs text-gray-500 dark:text-dark-text-tertiary">v2.0 Pattern Matching</p>
                </div>
              </div>

              <nav className="hidden md:flex space-x-1 ml-8">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const isActive = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                        isActive
                          ? 'bg-primary-50 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300'
                          : 'text-gray-600 dark:text-dark-text-secondary hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary'
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="font-medium">{item.label}</span>
                    </Link>
                  );
                })}
              </nav>
            </div>

            <div className="flex items-center space-x-4">
              {health && (
                <div className="hidden md:flex items-center space-x-2 text-sm">
                  <div
                    className={`w-2 h-2 rounded-full ${
                      health.status === 'healthy' ? 'bg-green-500 dark:bg-green-400' : 'bg-red-500 dark:bg-red-400'
                    }`}
                  />
                  <span className="text-gray-600 dark:text-dark-text-secondary">
                    {health.indices_loaded} indices | {health.total_vectors} vectors
                  </span>
                </div>
              )}

              <ThemeToggle />

              <a
                href="https://github.com/anthropics/spinanalyzer"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 dark:text-dark-text-secondary hover:text-gray-900 dark:hover:text-dark-text-primary transition-colors"
              >
                <Github className="w-5 h-5" />
              </a>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-dark-bg-secondary border-t border-gray-200 dark:border-gray-700 mt-auto transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center text-sm text-gray-500 dark:text-dark-text-tertiary">
            <p>
              SpinAnalyzer v{health?.version || '2.0.0'} - Pattern Matching Engine for Poker
            </p>
            <p>
              Uptime: {health ? Math.floor(health.uptime_seconds / 60) : 0}m
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
