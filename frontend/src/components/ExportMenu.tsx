import { useState, useRef, useEffect } from 'react';
import { Download, FileText, FileJson, Copy, Check } from 'lucide-react';

export interface ExportOption {
  label: string;
  icon: typeof FileText;
  onClick: () => void;
}

interface ExportMenuProps {
  options: ExportOption[];
  label?: string;
}

export default function ExportMenu({ options, label = 'Export' }: ExportMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    if (copied) {
      const timer = setTimeout(() => setCopied(false), 2000);
      return () => clearTimeout(timer);
    }
  }, [copied]);

  const handleOptionClick = (option: ExportOption) => {
    option.onClick();
    setIsOpen(false);

    // Show copied indicator if it's a copy action
    if (option.label.toLowerCase().includes('copy')) {
      setCopied(true);
    }
  };

  return (
    <div className="relative inline-block" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="btn btn-secondary flex items-center space-x-2"
      >
        {copied ? (
          <>
            <Check className="w-4 h-4" />
            <span>Copied!</span>
          </>
        ) : (
          <>
            <Download className="w-4 h-4" />
            <span>{label}</span>
          </>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-48 rounded-lg shadow-lg bg-white dark:bg-dark-bg-secondary border border-gray-200 dark:border-gray-700 z-50">
          <div className="py-1">
            {options.map((option, index) => {
              const Icon = option.icon;
              return (
                <button
                  key={index}
                  onClick={() => handleOptionClick(option)}
                  className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 dark:text-dark-text-primary hover:bg-gray-100 dark:hover:bg-dark-bg-tertiary transition-colors"
                >
                  <Icon className="w-4 h-4" />
                  <span>{option.label}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// Convenience exports for common icons
export { FileText, FileJson, Copy };
