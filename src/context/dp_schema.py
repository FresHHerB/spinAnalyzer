"""Pydantic v2 schema for a fully-enriched Decision Point.

Validated on emit by the v2 extractor; a DP that fails validation is
dropped (with a warning) rather than silently corrupting downstream
parquet/FAISS pipelines.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BoardTexture(BaseModel):
    """Board texture flags (extension of v1 _analyze_board_texture)."""

    monotone: bool = False
    two_tone: bool = False
    rainbow: bool = False
    paired: bool = False
    trips: bool = False
    connected: bool = False
    disconnected: bool = False
    high_broadway: bool = False
    low: bool = False
    wet: bool = False


class DrawsBlock(BaseModel):
    """Subset of src.hand_eval.draws.Draws as plain bools/int."""

    nut_flush_draw: bool = False
    weak_flush_draw: bool = False
    has_oesd: bool = False
    has_double_gutshot: bool = False
    has_gutshot: bool = False
    has_combo_draw: bool = False
    has_bdfd: bool = False
    has_bdsd: bool = False
    has_overcard_draw: bool = False
    has_pair_plus_draw: bool = False
    outs_count: int = 0


class BlockersBlock(BaseModel):
    """Subset of src.hand_eval.blockers.Blockers."""

    blocks_nut_flush: bool = False
    blocks_nut_straight: bool = False
    blocks_top_set: bool = False
    blocks_top_two_pair: bool = False
    has_ace_high_blocker: bool = False
    has_king_high_blocker: bool = False


class DecisionPoint(BaseModel):
    """One villain decision, fully enriched.

    Field naming preserves v1 column names where possible so downstream
    code (vectorizer encoders) can be reused.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    # Identity
    decision_id: str = Field(..., description="{hand_id}_{step_idx}")
    hand_id: str
    villain_name: str
    hero_name: str
    step_idx: int = Field(..., ge=0)

    # Temporal
    street: str  # preflop / flop / turn / river
    action_number_in_street: int = Field(..., ge=0)

    # Game state
    pot_bb: float = Field(..., ge=0.0)
    eff_stack_bb: float = Field(..., ge=0.0)
    spr: float | None = None  # None preflop or pot=0

    # Position
    villain_position: str  # IP / OOP / BTN / BB / SB
    hero_position: str

    # Action history
    preflop_sequence: list[str] = Field(default_factory=list)
    current_street_sequence: list[str] = Field(default_factory=list)
    action_path: str = ""  # canonical path string for this street

    # Aggressor
    preflop_aggressor: str | None = None  # 'hero' / 'villain' / None
    current_aggressor: str | None = None

    # Board
    board_cards: list[str] = Field(default_factory=list)
    board_texture: BoardTexture = Field(default_factory=BoardTexture)

    # Holdings (when revealed)
    villain_hand: list[str] | None = None
    villain_hand_strength: str | None = None  # ONE_PAIR / FLUSH / etc
    villain_made_specific: str | None = None  # TPTK / nut_flush / ...
    villain_hand_rank_int: int | None = None
    villain_draws: DrawsBlock | None = None
    villain_blockers: BlockersBlock | None = None
    villain_equity_vs_random: float | None = Field(default=None, ge=0.0, le=1.0)

    # Intent + line
    intent: str | None = None  # value_pure / bluff_pure / etc
    line_tag: str | None = None  # cbet / donk / xr / etc

    # Action taken (TARGET)
    villain_action: str  # check / call / bet / raise / fold / all_in
    villain_bet_size_bb: float | None = None
    villain_bet_size_pot_pct: float | None = None

    # Outcome
    went_to_showdown: bool = False
    villain_won: bool | None = None
