import axios from 'axios';
import type {
  VillainInfo,
  VillainStats,
  DecisionPoint,
  SearchResult,
  HealthStatus,
  ContextSearchRequest,
  SimilaritySearchRequest,
  RangeAnalysisRequest,
  RangeAnalysisResponse,
} from '@/types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Health Check
export const getHealth = async (): Promise<HealthStatus> => {
  const { data } = await api.get<HealthStatus>('/health');
  return data;
};

// Villains
export const getVillains = async (): Promise<{ total_villains: number; villains: VillainInfo[] }> => {
  const { data } = await api.get('/villains');
  return data;
};

export const getVillain = async (name: string): Promise<VillainInfo> => {
  const { data } = await api.get<VillainInfo>(`/villain/${name}`);
  return data;
};

export const getVillainStats = async (name: string): Promise<VillainStats> => {
  const { data } = await api.get<VillainStats>(`/villain/${name}/stats`);
  return data;
};

// Search
export const searchByContext = async (request: ContextSearchRequest): Promise<SearchResult> => {
  const { data } = await api.post<SearchResult>('/search/context', request);
  return data;
};

export const searchBySimilarity = async (request: SimilaritySearchRequest): Promise<SearchResult> => {
  const { data } = await api.post<SearchResult>('/search/similarity', request);
  return data;
};

export const analyzeRange = async (request: RangeAnalysisRequest): Promise<RangeAnalysisResponse> => {
  const { data } = await api.post<RangeAnalysisResponse>('/search/range-analysis', request);
  return data;
};

// Decisions & Hands
export const getDecision = async (id: string): Promise<DecisionPoint> => {
  const { data } = await api.get<DecisionPoint>(`/decision/${id}`);
  return data;
};

export const getHandHistory = async (handId: string): Promise<{
  hand_id: string;
  villain_name: string;
  decision_points: DecisionPoint[];
  total_decision_points: number;
}> => {
  const { data } = await api.get(`/hand/${handId}`);
  return data;
};

export default api;
