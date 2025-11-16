// API Types matching backend Pydantic models

export type Street = 'preflop' | 'flop' | 'turn' | 'river';
export type Position = 'IP' | 'OOP' | 'BTN' | 'BB';

export interface DecisionPoint {
  decision_id: string;
  hand_id: string;
  villain_name: string;
  street: Street;
  villain_position: Position;
  villain_action: string;
  pot_bb: number;
  eff_stack_bb?: number;
  spr?: number;
  board_cards?: string[];
  board_texture?: Record<string, any>;
  villain_bet_size_bb?: number;
  villain_bet_size_pot_pct?: number;
  preflop_sequence?: string[];
  current_street_sequence?: string[];
  went_to_showdown?: boolean;
  villain_won?: boolean;
  distance?: number;

  // Hand replayer fields
  preflop_actions?: string;
  flop_actions?: string;
  turn_actions?: string;
  river_actions?: string;
  flop_board?: string;
  turn_board?: string;
  river_board?: string;
  villain_stack_bb?: number;
  hero_stack_bb?: number;
  hero_position?: Position;
}

export interface VillainInfo {
  name: string;
  total_decision_points: number;
  indexed_vectors: number;
  streets: Record<string, number>;
  positions: Record<string, number>;
  top_actions: Record<string, number>;
  avg_pot_bb: number;
  avg_spr?: number;
}

export interface SearchResult {
  query_info: Record<string, any>;
  results: DecisionPoint[];
  total_results: number;
  search_time_ms: number;
}

export interface VillainStats {
  villain: VillainInfo;
  action_distribution: Record<string, Record<string, number>>;
  pot_size_distribution: Record<string, number>;
  spr_distribution: Record<string, number>;
  position_stats: Record<string, any>;
}

export interface HealthStatus {
  status: string;
  version: string;
  indices_loaded: number;
  total_vectors: number;
  uptime_seconds: number;
}

// Request Types
export interface ContextSearchRequest {
  villain_name: string;
  street?: Street;
  position?: Position;
  pot_bb_min?: number;
  pot_bb_max?: number;
  spr_min?: number;
  spr_max?: number;
  k?: number;
}

export interface SimilaritySearchRequest {
  villain_name: string;
  query_vector: number[];
  k?: number;
}

export interface RangeAnalysisRequest {
  villain_name: string;
  street?: Street;
  position?: Position;
  action?: string;
  pot_bb_min?: number;
  pot_bb_max?: number;
}

export interface HandStrengthDistribution {
  count: number;
  percentage: number;
}

export interface RangeAnalysisExample {
  hand_id: string;
  street: string;
  action: string;
  pot_bb: number;
  villain_hand: string;
  hand_strength: string;
  board: string;
  draws: string;
}

export interface RangeAnalysisResponse {
  total_samples: number;
  hand_strength_distribution: Record<string, HandStrengthDistribution>;
  draws_distribution: Record<string, HandStrengthDistribution>;
  board_texture_distribution: Record<string, HandStrengthDistribution>;
  action_distribution: Record<string, HandStrengthDistribution>;
  examples: RangeAnalysisExample[];
  search_time_ms: number;
}
