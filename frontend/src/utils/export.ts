import type { DecisionPoint, VillainStats } from '@/types';

/**
 * Convert array of objects to CSV format
 */
function arrayToCSV(data: any[], headers?: string[]): string {
  if (data.length === 0) return '';

  // Get headers from first object if not provided
  const csvHeaders = headers || Object.keys(data[0]);

  // Create header row
  const headerRow = csvHeaders.join(',');

  // Create data rows
  const dataRows = data.map(row => {
    return csvHeaders.map(header => {
      const value = row[header];

      // Handle null/undefined
      if (value === null || value === undefined) return '';

      // Handle strings with commas or quotes
      if (typeof value === 'string' && (value.includes(',') || value.includes('"') || value.includes('\n'))) {
        return `"${value.replace(/"/g, '""')}"`;
      }

      return value;
    }).join(',');
  });

  return [headerRow, ...dataRows].join('\n');
}

/**
 * Download a file with given content
 */
function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export decision points to CSV
 */
export function exportDecisionPointsToCSV(decisionPoints: DecisionPoint[], filename?: string) {
  const csvHeaders = [
    'decision_id',
    'hand_id',
    'villain_name',
    'street',
    'villain_position',
    'hero_position',
    'villain_action',
    'pot_bb',
    'villain_stack_bb',
    'hero_stack_bb',
    'spr',
    'villain_bet_size_bb',
    'flop_board',
    'turn_board',
    'river_board',
    'distance'
  ];

  const csvContent = arrayToCSV(decisionPoints, csvHeaders);
  const defaultFilename = `spinanalyzer_results_${new Date().toISOString().split('T')[0]}.csv`;

  downloadFile(csvContent, filename || defaultFilename, 'text/csv;charset=utf-8;');
}

/**
 * Export decision points to JSON
 */
export function exportDecisionPointsToJSON(decisionPoints: DecisionPoint[], filename?: string) {
  const jsonContent = JSON.stringify(decisionPoints, null, 2);
  const defaultFilename = `spinanalyzer_results_${new Date().toISOString().split('T')[0]}.json`;

  downloadFile(jsonContent, filename || defaultFilename, 'application/json;charset=utf-8;');
}

/**
 * Export villain stats to CSV
 */
export function exportVillainStatsToCSV(stats: VillainStats, filename?: string) {
  // Flatten the stats into multiple CSV sections

  // Basic info
  const basicInfo = [{
    villain_name: stats.villain.name,
    total_decision_points: stats.villain.total_decision_points,
    indexed_vectors: stats.villain.indexed_vectors,
    avg_pot_bb: stats.villain.avg_pot_bb.toFixed(2),
    avg_spr: stats.villain.avg_spr?.toFixed(2) || 'N/A',
  }];

  // Streets distribution
  const streetsData = Object.entries(stats.villain.streets).map(([street, count]) => ({
    street,
    count,
    percentage: ((count / stats.villain.total_decision_points) * 100).toFixed(1) + '%'
  }));

  // Positions distribution
  const positionsData = Object.entries(stats.villain.positions).map(([position, count]) => ({
    position,
    count,
    percentage: ((count / stats.villain.total_decision_points) * 100).toFixed(1) + '%'
  }));

  // Top actions
  const actionsData = Object.entries(stats.villain.top_actions).map(([action, count]) => ({
    action,
    count,
    percentage: ((count / stats.villain.total_decision_points) * 100).toFixed(1) + '%'
  }));

  // Combine all sections
  const csvContent = [
    '# Basic Information',
    arrayToCSV(basicInfo),
    '',
    '# Street Distribution',
    arrayToCSV(streetsData),
    '',
    '# Position Distribution',
    arrayToCSV(positionsData),
    '',
    '# Top Actions',
    arrayToCSV(actionsData),
  ].join('\n');

  const defaultFilename = `${stats.villain.name}_stats_${new Date().toISOString().split('T')[0]}.csv`;

  downloadFile(csvContent, filename || defaultFilename, 'text/csv;charset=utf-8;');
}

/**
 * Export villain stats to JSON
 */
export function exportVillainStatsToJSON(stats: VillainStats, filename?: string) {
  const jsonContent = JSON.stringify(stats, null, 2);
  const defaultFilename = `${stats.villain.name}_stats_${new Date().toISOString().split('T')[0]}.json`;

  downloadFile(jsonContent, filename || defaultFilename, 'application/json;charset=utf-8;');
}

/**
 * Copy data to clipboard as JSON
 */
export async function copyToClipboard(data: any): Promise<boolean> {
  try {
    const jsonString = JSON.stringify(data, null, 2);
    await navigator.clipboard.writeText(jsonString);
    return true;
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
}
