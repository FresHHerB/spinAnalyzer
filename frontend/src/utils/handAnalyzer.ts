/**
 * Hand Analyzer - Classifica força de mão e textura de board
 */

export type HandStrength =
  | 'nuts'
  | 'top_pair'
  | 'middle_pair'
  | 'bottom_pair'
  | 'weak_pair'
  | 'two_pair'
  | 'trips'
  | 'straight'
  | 'flush'
  | 'full_house'
  | 'quads'
  | 'straight_flush';

export type DrawType =
  | 'oesd' // Open-ended straight draw
  | 'gutshot'
  | 'flush_draw'
  | 'bdfd' // Backdoor flush draw
  | 'combo_draw'
  | 'straight_flush_draw'
  | 'no_draw';

export type HandCategory =
  | 'value_strong' // Top pair+, sets, two pair
  | 'value_medium' // Middle pair, weak top pair
  | 'value_weak' // Bottom pair, ace high
  | 'draw_strong' // OESD, flush draw, combo draw
  | 'draw_weak' // Gutshot, BDFD
  | 'bluff_pure' // Air, no pair no draw
  | 'bluff_semi' // Weak pair + draw
  | 'showdown_medium'; // Hands that can check for showdown value

export interface BoardTexture {
  wetness: 'dry' | 'semi_wet' | 'wet';
  suits: number; // Number of different suits
  connected: boolean; // Cards are connected (like 8-9-10)
  paired: boolean;
  monotone: boolean; // All same suit
  rainbow: boolean; // All different suits
  straightPossible: boolean;
  flushPossible: boolean;
  draws: string[]; // Possible draws on this board
}

export interface HandAnalysis {
  handStrength: HandStrength;
  drawType: DrawType;
  category: HandCategory;
  isValueBet: boolean;
  isBluff: boolean;
  isSemiBluff: boolean;
  equity: number; // Estimated equity (0-100)
  description: string;
}

/**
 * Parse card notation (e.g., "As" = Ace of Spades)
 */
export function parseCard(card: string): { rank: string; suit: string; value: number } | null {
  if (!card || card.length !== 2) return null;

  const rank = card[0];
  const suit = card[1];

  const rankValues: Record<string, number> = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
    'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
  };

  return {
    rank,
    suit,
    value: rankValues[rank] || 0
  };
}

/**
 * Analyze board texture
 */
export function analyzeBoardTexture(board: string): BoardTexture {
  const cards = board.replace(/\s/g, '').match(/.{1,2}/g) || [];
  const parsedCards = cards.map(parseCard).filter(c => c !== null) as Array<{ rank: string; suit: string; value: number }>;

  if (parsedCards.length === 0) {
    return {
      wetness: 'dry',
      suits: 0,
      connected: false,
      paired: false,
      monotone: false,
      rainbow: false,
      straightPossible: false,
      flushPossible: false,
      draws: []
    };
  }

  // Analyze suits
  const suits = new Set(parsedCards.map(c => c.suit));
  const suitCounts = parsedCards.reduce((acc, c) => {
    acc[c.suit] = (acc[c.suit] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const maxSuitCount = Math.max(...Object.values(suitCounts));

  // Analyze ranks
  const ranks = parsedCards.map(c => c.value).sort((a, b) => a - b);
  const rankSet = new Set(ranks);

  // Check for pairs
  const paired = rankSet.size < ranks.length;

  // Check connectivity
  let connected = false;
  if (ranks.length >= 2) {
    const gaps = ranks.slice(1).map((r, i) => r - ranks[i]);
    connected = gaps.every(g => g <= 2); // Cards within 2 ranks of each other
  }

  // Check for straight possibilities
  const straightPossible = ranks.length >= 3 && (
    (ranks[ranks.length - 1] - ranks[0]) <= 4 || // Regular straight
    (ranks.includes(14) && ranks.includes(2)) // Wheel possibility
  );

  // Monotone/rainbow
  const monotone = suits.size === 1;
  const rainbow = suits.size === parsedCards.length;
  const flushPossible = maxSuitCount >= 2;

  // Determine wetness
  let wetness: 'dry' | 'semi_wet' | 'wet' = 'dry';
  if (straightPossible && flushPossible) wetness = 'wet';
  else if (straightPossible || flushPossible || connected) wetness = 'semi_wet';

  // Identify possible draws
  const draws: string[] = [];
  if (maxSuitCount === 2) draws.push('BDFD');
  if (maxSuitCount >= 3) draws.push('Flush Draw');
  if (straightPossible) draws.push('Straight Draw');
  if (connected && straightPossible) draws.push('Combo Draw Possible');

  return {
    wetness,
    suits: suits.size,
    connected,
    paired,
    monotone,
    rainbow,
    straightPossible,
    flushPossible,
    draws
  };
}

/**
 * Classify hand category based on action and board
 */
export function classifyHandCategory(
  action: string,
  board: string,
  street: string,
  potSize: number,
  betSize?: number
): HandCategory {
  const boardTexture = analyzeBoardTexture(board);
  const actionLower = action.toLowerCase();

  // Aggressive actions (bet, raise)
  if (actionLower.includes('bet') || actionLower.includes('raise')) {
    // Large bet on wet board = likely strong value or strong draw
    if (betSize && betSize > potSize * 0.66) {
      if (boardTexture.wetness === 'wet') {
        return 'value_strong'; // Protecting against draws
      }
      return 'value_strong'; // Polarized bet
    }

    // Medium bet on any board
    if (betSize && betSize >= potSize * 0.33) {
      if (boardTexture.straightPossible || boardTexture.flushPossible) {
        return 'draw_strong'; // Could be semi-bluff with draw
      }
      return 'value_medium'; // Medium value or merge
    }

    // Small bet (probe, blocking)
    if (betSize && betSize < potSize * 0.33) {
      if (street === 'turn' || street === 'river') {
        return 'bluff_semi'; // Probe bet, often weak
      }
      return 'value_weak';
    }

    // Default bet/raise
    if (boardTexture.wetness === 'wet') {
      return 'draw_strong';
    }
    return 'value_medium';
  }

  // Passive actions (call, check)
  if (actionLower.includes('call')) {
    if (boardTexture.draws.length > 0) {
      return 'draw_weak'; // Drawing hand
    }
    return 'showdown_medium'; // Marginal made hand
  }

  if (actionLower.includes('check')) {
    return 'showdown_medium'; // Pot control or weak made hand
  }

  // Fold
  if (actionLower.includes('fold')) {
    return 'bluff_pure'; // Had nothing
  }

  return 'showdown_medium';
}

/**
 * Get category display info
 */
export function getCategoryInfo(category: HandCategory): {
  label: string;
  color: string;
  description: string;
  examples: string[];
} {
  const categoryMap = {
    value_strong: {
      label: 'Valor Forte',
      color: '#10b981', // green
      description: 'Top pair+, sets, two pair, trips, straights',
      examples: ['Top Pair Top Kicker', 'Overpair', 'Set', 'Two Pair', 'Straight', 'Flush']
    },
    value_medium: {
      label: 'Valor Médio',
      color: '#0ea5e9', // blue
      description: 'Middle pair, weak top pair, good ace high',
      examples: ['Top Pair Weak Kicker', 'Middle Pair', 'Ace High (good)', 'Weak Two Pair']
    },
    value_weak: {
      label: 'Valor Fraco',
      color: '#f59e0b', // yellow
      description: 'Bottom pair, weak pair, marginal showdown',
      examples: ['Bottom Pair', 'Underpair', 'Weak Ace High', 'Third Pair']
    },
    draw_strong: {
      label: 'Draw Forte',
      color: '#8b5cf6', // purple
      description: 'OESD, flush draw, combo draw, straight flush draw',
      examples: ['Flush Draw', 'OESD', 'Combo Draw (FD + SD)', 'Straight Flush Draw']
    },
    draw_weak: {
      label: 'Draw Fraco',
      color: '#ec4899', // pink
      description: 'Gutshot, backdoor draws, weak draws',
      examples: ['Gutshot', 'BDFD (Backdoor Flush Draw)', 'BDSD (Backdoor Straight Draw)']
    },
    bluff_pure: {
      label: 'Blefe Puro',
      color: '#ef4444', // red
      description: 'Ar completo, sem par e sem draw',
      examples: ['Ace High (no draw)', 'King High', 'Queen High', 'Complete Air']
    },
    bluff_semi: {
      label: 'Semi-Blefe',
      color: '#f97316', // orange
      description: 'Par fraco + draw, ou draw fraco',
      examples: ['Bottom Pair + BDFD', 'Gutshot + Pair', 'Overcards + Draw']
    },
    showdown_medium: {
      label: 'Showdown Médio',
      color: '#06b6d4', // cyan
      description: 'Mãos que preferem ver showdown',
      examples: ['Middle Pair (passive)', 'Weak Top Pair', 'Ace High', 'Pocket Pair']
    }
  };

  return categoryMap[category];
}

/**
 * Estimate equity based on category
 */
export function estimateEquity(category: HandCategory): number {
  const equityMap: Record<HandCategory, number> = {
    value_strong: 75,
    value_medium: 60,
    value_weak: 45,
    draw_strong: 50,
    draw_weak: 30,
    bluff_pure: 15,
    bluff_semi: 40,
    showdown_medium: 50
  };

  return equityMap[category];
}
