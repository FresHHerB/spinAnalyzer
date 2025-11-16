import { Moon, Sun } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';

export default function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      className="relative inline-flex items-center justify-center w-10 h-10 rounded-lg
                 bg-gray-100 hover:bg-gray-200 dark:bg-dark-bg-tertiary dark:hover:bg-gray-600
                 transition-all duration-200 focus:outline-none focus:ring-2
                 focus:ring-primary-500 dark:focus:ring-primary-400"
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {/* Sun icon for light mode */}
      <Sun
        className={`absolute w-5 h-5 text-yellow-600 transition-all duration-300
                   ${theme === 'light'
                     ? 'rotate-0 scale-100 opacity-100'
                     : 'rotate-90 scale-0 opacity-0'
                   }`}
      />

      {/* Moon icon for dark mode */}
      <Moon
        className={`absolute w-5 h-5 text-slate-300 transition-all duration-300
                   ${theme === 'dark'
                     ? 'rotate-0 scale-100 opacity-100'
                     : '-rotate-90 scale-0 opacity-0'
                   }`}
      />
    </button>
  );
}
