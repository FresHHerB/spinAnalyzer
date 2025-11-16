/**
 * Saved Queries Utility
 * Manages saved search queries with localStorage persistence
 */

export interface SavedQuery {
  id: string;
  name: string;
  description?: string;
  villain_name: string;
  street?: string;
  position?: string;
  action?: string;
  pot_bb_min?: number;
  pot_bb_max?: number;
  created_at: string;
  last_used?: string;
  use_count: number;
}

const STORAGE_KEY = 'spinanalyzer-saved-queries';

/**
 * Load all saved queries from localStorage
 */
export function loadSavedQueries(): SavedQuery[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];

    const queries = JSON.parse(stored) as SavedQuery[];
    return queries.sort((a, b) => {
      // Sort by last_used descending, then by created_at descending
      if (a.last_used && b.last_used) {
        return new Date(b.last_used).getTime() - new Date(a.last_used).getTime();
      }
      if (a.last_used) return -1;
      if (b.last_used) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  } catch (error) {
    console.error('Error loading saved queries:', error);
    return [];
  }
}

/**
 * Save a new query
 */
export function saveQuery(query: Omit<SavedQuery, 'id' | 'created_at' | 'use_count'>): SavedQuery {
  const queries = loadSavedQueries();

  const newQuery: SavedQuery = {
    ...query,
    id: generateId(),
    created_at: new Date().toISOString(),
    use_count: 0,
  };

  queries.push(newQuery);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));

  return newQuery;
}

/**
 * Update an existing query
 */
export function updateQuery(id: string, updates: Partial<SavedQuery>): boolean {
  const queries = loadSavedQueries();
  const index = queries.findIndex(q => q.id === id);

  if (index === -1) return false;

  queries[index] = { ...queries[index], ...updates };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));

  return true;
}

/**
 * Delete a query
 */
export function deleteQuery(id: string): boolean {
  const queries = loadSavedQueries();
  const filtered = queries.filter(q => q.id !== id);

  if (filtered.length === queries.length) return false;

  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  return true;
}

/**
 * Mark a query as used (increment use_count and update last_used)
 */
export function markQueryUsed(id: string): void {
  const queries = loadSavedQueries();
  const query = queries.find(q => q.id === id);

  if (!query) return;

  query.use_count += 1;
  query.last_used = new Date().toISOString();

  localStorage.setItem(STORAGE_KEY, JSON.stringify(queries));
}

/**
 * Get a single query by ID
 */
export function getQuery(id: string): SavedQuery | undefined {
  const queries = loadSavedQueries();
  return queries.find(q => q.id === id);
}

/**
 * Search saved queries by name or description
 */
export function searchQueries(searchTerm: string): SavedQuery[] {
  const queries = loadSavedQueries();
  const term = searchTerm.toLowerCase();

  return queries.filter(q =>
    q.name.toLowerCase().includes(term) ||
    q.description?.toLowerCase().includes(term) ||
    q.villain_name.toLowerCase().includes(term)
  );
}

/**
 * Get most frequently used queries
 */
export function getMostUsedQueries(limit: number = 5): SavedQuery[] {
  const queries = loadSavedQueries();
  return queries
    .sort((a, b) => b.use_count - a.use_count)
    .slice(0, limit);
}

/**
 * Export queries as JSON
 */
export function exportQueries(): string {
  const queries = loadSavedQueries();
  return JSON.stringify(queries, null, 2);
}

/**
 * Import queries from JSON
 */
export function importQueries(jsonString: string, mode: 'replace' | 'merge' = 'merge'): boolean {
  try {
    const imported = JSON.parse(jsonString) as SavedQuery[];

    if (!Array.isArray(imported)) {
      throw new Error('Invalid format: expected array of queries');
    }

    if (mode === 'replace') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(imported));
    } else {
      const existing = loadSavedQueries();
      const merged = [...existing];

      for (const query of imported) {
        // Check if ID already exists
        const existingIndex = merged.findIndex(q => q.id === query.id);
        if (existingIndex >= 0) {
          // Generate new ID to avoid conflicts
          merged.push({ ...query, id: generateId() });
        } else {
          merged.push(query);
        }
      }

      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
    }

    return true;
  } catch (error) {
    console.error('Error importing queries:', error);
    return false;
  }
}

/**
 * Clear all saved queries
 */
export function clearAllQueries(): void {
  localStorage.removeItem(STORAGE_KEY);
}

/**
 * Generate a unique ID
 */
function generateId(): string {
  return `query_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Get query statistics
 */
export function getQueryStats(): {
  total: number;
  totalUses: number;
  mostUsed?: SavedQuery;
  recentlyUsed?: SavedQuery;
} {
  const queries = loadSavedQueries();

  if (queries.length === 0) {
    return { total: 0, totalUses: 0 };
  }

  const totalUses = queries.reduce((sum, q) => sum + q.use_count, 0);
  const mostUsed = queries.reduce((max, q) => q.use_count > max.use_count ? q : max);
  const recentlyUsed = queries
    .filter(q => q.last_used)
    .sort((a, b) => new Date(b.last_used!).getTime() - new Date(a.last_used!).getTime())[0];

  return {
    total: queries.length,
    totalUses,
    mostUsed,
    recentlyUsed,
  };
}
