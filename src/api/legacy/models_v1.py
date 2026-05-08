"""
Pydantic models for API request/response validation
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class StreetEnum(str, Enum):
    """Street options"""
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


class PositionEnum(str, Enum):
    """Position options"""
    IP = "IP"
    OOP = "OOP"
    BTN = "BTN"
    BB = "BB"


class SimilaritySearchRequest(BaseModel):
    """Request model for similarity search"""
    villain_name: str = Field(..., description="Name of the villain to search within")
    query_vector: List[float] = Field(..., description="99-dimensional query vector", min_items=99, max_items=99)
    k: int = Field(default=10, description="Number of results to return", ge=1, le=100)

    class Config:
        schema_extra = {
            "example": {
                "villain_name": "BahTOBUK",
                "query_vector": [0.0] * 99,
                "k": 10
            }
        }


class ContextSearchRequest(BaseModel):
    """Request model for context-based search"""
    villain_name: str = Field(..., description="Name of the villain to search within")
    street: Optional[StreetEnum] = Field(None, description="Street filter")
    position: Optional[PositionEnum] = Field(None, description="Position filter")
    pot_bb_min: Optional[float] = Field(None, description="Minimum pot size in BB", ge=0)
    pot_bb_max: Optional[float] = Field(None, description="Maximum pot size in BB", ge=0)
    spr_min: Optional[float] = Field(None, description="Minimum SPR", ge=0)
    spr_max: Optional[float] = Field(None, description="Maximum SPR", ge=0)
    k: int = Field(default=10, description="Number of results to return", ge=1, le=100)

    class Config:
        schema_extra = {
            "example": {
                "villain_name": "BahTOBUK",
                "street": "preflop",
                "position": "BTN",
                "pot_bb_min": 5.0,
                "pot_bb_max": 20.0,
                "k": 10
            }
        }


class DecisionPointResponse(BaseModel):
    """Response model for a decision point"""
    decision_id: str
    hand_id: str
    villain_name: str
    street: str
    villain_position: str
    villain_action: str
    pot_bb: float
    eff_stack_bb: Optional[float]
    spr: Optional[float]
    board_cards: Optional[List[str]]
    board_texture: Optional[Dict[str, Any]]
    villain_bet_size_bb: Optional[float]
    villain_bet_size_pot_pct: Optional[float]
    preflop_sequence: Optional[List[str]]
    current_street_sequence: Optional[List[str]]
    went_to_showdown: Optional[bool]
    villain_won: Optional[bool]
    distance: Optional[float] = Field(None, description="Distance from query (in search results)")


class SearchResult(BaseModel):
    """Response model for search results"""
    query_info: Dict[str, Any]
    results: List[DecisionPointResponse]
    total_results: int
    search_time_ms: float


class VillainInfo(BaseModel):
    """Response model for villain information"""
    name: str
    total_decision_points: int
    indexed_vectors: int
    streets: Dict[str, int]
    positions: Dict[str, int]
    top_actions: Dict[str, int]
    avg_pot_bb: float
    avg_spr: Optional[float]


class VillainsListResponse(BaseModel):
    """Response model for villains list"""
    total_villains: int
    villains: List[VillainInfo]


class VillainStatsResponse(BaseModel):
    """Response model for detailed villain stats"""
    villain: VillainInfo
    action_distribution: Dict[str, Dict[str, int]]  # By street
    pot_size_distribution: Dict[str, int]
    spr_distribution: Dict[str, int]
    position_stats: Dict[str, Any]


class HandHistoryResponse(BaseModel):
    """Response model for hand history"""
    hand_id: str
    villain_name: str
    decision_points: List[DecisionPointResponse]
    total_decision_points: int


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    version: str
    indices_loaded: int
    total_vectors: int
    uptime_seconds: float


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None


class RangeAnalysisRequest(BaseModel):
    """Request model for range analysis"""
    villain_name: str = Field(..., description="Name of the villain to analyze")
    street: Optional[StreetEnum] = Field(None, description="Street filter")
    position: Optional[PositionEnum] = Field(None, description="Position filter")
    action: Optional[str] = Field(None, description="Action filter (bet, raise, call, check, fold)")
    pot_bb_min: Optional[float] = Field(None, description="Minimum pot size in BB", ge=0)
    pot_bb_max: Optional[float] = Field(None, description="Maximum pot size in BB", ge=0)

    class Config:
        schema_extra = {
            "example": {
                "villain_name": "Tipatushka",
                "street": "turn",
                "action": "bet",
                "pot_bb_min": 5.0,
                "pot_bb_max": 15.0
            }
        }


class HandStrengthDistribution(BaseModel):
    """Distribution of hand strengths"""
    count: int
    percentage: float


class RangeAnalysisExample(BaseModel):
    """Example hand from range analysis"""
    hand_id: str
    street: str
    action: str
    pot_bb: float
    villain_hand: str
    hand_strength: str
    board: str
    draws: str


class RangeAnalysisResponse(BaseModel):
    """Response model for range analysis"""
    total_samples: int
    hand_strength_distribution: Dict[str, HandStrengthDistribution]
    draws_distribution: Dict[str, HandStrengthDistribution]
    board_texture_distribution: Dict[str, HandStrengthDistribution]
    action_distribution: Dict[str, HandStrengthDistribution]
    examples: List[RangeAnalysisExample]
    search_time_ms: float
