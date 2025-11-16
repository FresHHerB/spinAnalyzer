"""
SpinAnalyzer v2.0 - FastAPI Application
Main API entry point
"""

import sys
import time
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.indexing.build_indices import IndexBuilder
from src.vectorization.vectorizer import Vectorizer
from src.api.models import (
    SimilaritySearchRequest,
    ContextSearchRequest,
    SearchResult,
    DecisionPointResponse,
    VillainInfo,
    VillainsListResponse,
    VillainStatsResponse,
    HandHistoryResponse,
    HealthResponse,
    ErrorResponse,
    RangeAnalysisRequest,
    RangeAnalysisResponse,
)
from src.api.file_upload import router as upload_router

# Global state
app_state = {
    "start_time": time.time(),
    "index_builder": None,
    "vectorizer": None,
    "df": None,
    "indices_dir": Path("indices"),
    "data_file": Path("dataset/decision_points/decision_points_vectorized.parquet"),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("🚀 Starting SpinAnalyzer API v2.0...")

    # Load data
    logger.info(f"Loading data from {app_state['data_file']}...")
    app_state["df"] = pd.read_parquet(app_state["data_file"])
    logger.info(f"✓ Loaded {len(app_state['df'])} decision points")

    # Load street features for hand strength and draws
    street_features_file = Path("dataset/street_features.parquet")
    if street_features_file.exists():
        logger.info("Loading street features for hand strength analysis...")
        street_df = pd.read_parquet(street_features_file)

        # Merge hand strength and draw info into main dataframe
        # street_df has: hand_id, player (villain), street, hand_strength_lbl, draw_type, fd_flag, oe_flag, gs_flag
        merge_cols = ['hand_id', 'street', 'hand_strength_lbl', 'draw_type', 'fd_flag', 'oe_flag', 'gs_flag']
        street_df_subset = street_df[['hand_id', 'player', 'street', 'hand_strength_lbl', 'draw_type', 'fd_flag', 'oe_flag', 'gs_flag']].copy()
        street_df_subset = street_df_subset.rename(columns={'player': 'villain_name'})

        # Merge on hand_id, villain_name, and street
        app_state["df"] = app_state["df"].merge(
            street_df_subset,
            on=['hand_id', 'villain_name', 'street'],
            how='left'
        )

        # Update villain_hand_strength and villain_draws from the merged data
        app_state["df"]['villain_hand_strength'] = app_state["df"]['hand_strength_lbl'].fillna('Unknown')
        app_state["df"]['villain_draws'] = app_state["df"]['draw_type'].fillna('none')

        logger.info(f"✓ Merged hand strength data. {app_state['df']['hand_strength_lbl'].notna().sum()} rows with hand strength")
    else:
        logger.warning("street_features.parquet not found - hand strength analysis will be limited")

    # Initialize components
    logger.info("Initializing IndexBuilder...")
    app_state["index_builder"] = IndexBuilder(
        indices_dir=app_state["indices_dir"],
        dimension=99
    )

    logger.info("Initializing Vectorizer...")
    app_state["vectorizer"] = Vectorizer()  # Uses default config

    # Load summary
    summary = app_state["index_builder"].get_summary()
    logger.success(f"✓ API Ready! {summary['total_indices']} indices, {summary['total_vectors']} vectors")

    yield

    # Shutdown
    logger.info("Shutting down SpinAnalyzer API...")


# Create FastAPI app
app = FastAPI(
    title="SpinAnalyzer v2.0 API",
    description="Pattern Matching Engine for Poker Decision Analysis",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(upload_router)


# Helper functions
def get_decision_point_response(row: pd.Series, distance: Optional[float] = None) -> DecisionPointResponse:
    """Convert DataFrame row to DecisionPointResponse"""
    return DecisionPointResponse(
        decision_id=row["decision_id"],
        hand_id=row["hand_id"],
        villain_name=row["villain_name"],
        street=row["street"],
        villain_position=row["villain_position"],
        villain_action=row["villain_action"],
        pot_bb=float(row["pot_bb"]) if pd.notna(row["pot_bb"]) else 0.0,
        eff_stack_bb=float(row["eff_stack_bb"]) if pd.notna(row["eff_stack_bb"]) else None,
        spr=float(row["spr"]) if pd.notna(row["spr"]) else None,
        board_cards=row.get("board_cards"),
        board_texture=row.get("board_texture"),
        villain_bet_size_bb=float(row["villain_bet_size_bb"]) if pd.notna(row.get("villain_bet_size_bb")) else None,
        villain_bet_size_pot_pct=float(row["villain_bet_size_pot_pct"]) if pd.notna(row.get("villain_bet_size_pot_pct")) else None,
        preflop_sequence=row.get("preflop_sequence"),
        current_street_sequence=row.get("current_street_sequence"),
        went_to_showdown=bool(row["went_to_showdown"]) if pd.notna(row.get("went_to_showdown")) else None,
        villain_won=bool(row["villain_won"]) if pd.notna(row.get("villain_won")) else None,
        distance=float(distance) if distance is not None else None,
    )


def get_villain_info(villain_name: str, df: pd.DataFrame, index_builder: IndexBuilder) -> VillainInfo:
    """Get villain information"""
    villain_df = df[df["villain_name"] == villain_name]

    # Get indexed vectors count
    summary = index_builder.get_summary()
    villain_summary = next((v for v in summary["villains"] if v["name"] == villain_name), None)
    indexed_vectors = villain_summary["vectors"] if villain_summary else 0

    # Streets distribution
    streets = villain_df["street"].value_counts().to_dict()

    # Positions distribution
    positions = villain_df["villain_position"].value_counts().to_dict()

    # Top actions (top 5)
    top_actions = villain_df["villain_action"].value_counts().head(5).to_dict()

    # Average pot size
    avg_pot = float(villain_df["pot_bb"].mean())

    # Average SPR
    avg_spr = float(villain_df["spr"].mean()) if villain_df["spr"].notna().any() else None

    return VillainInfo(
        name=villain_name,
        total_decision_points=len(villain_df),
        indexed_vectors=indexed_vectors,
        streets=streets,
        positions=positions,
        top_actions=top_actions,
        avg_pot_bb=avg_pot,
        avg_spr=avg_spr,
    )


# API Endpoints

@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "SpinAnalyzer v2.0 Pattern Matching API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    summary = app_state["index_builder"].get_summary()
    uptime = time.time() - app_state["start_time"]

    return HealthResponse(
        status="healthy",
        version="2.0.0",
        indices_loaded=summary["total_indices"],
        total_vectors=summary["total_vectors"],
        uptime_seconds=uptime,
    )


@app.post("/search/similarity", response_model=SearchResult, tags=["Search"])
async def search_similarity(request: SimilaritySearchRequest):
    """
    Search for similar decision points using a query vector

    Returns the k most similar decision points for the specified villain.
    """
    start_time = time.perf_counter()

    try:
        # Validate villain exists
        df = app_state["df"]
        if request.villain_name not in df["villain_name"].unique():
            raise HTTPException(
                status_code=404,
                detail=f"Villain '{request.villain_name}' not found in dataset"
            )

        # Convert query vector to numpy array
        query_vec = np.array(request.query_vector, dtype=np.float32)

        # Validate vector dimension
        if query_vec.shape[0] != 99:
            raise HTTPException(
                status_code=400,
                detail=f"Query vector must be 99-dimensional, got {query_vec.shape[0]}"
            )

        # Perform search
        index_builder = app_state["index_builder"]
        distances, indices, decision_ids = index_builder.search(
            villain_name=request.villain_name,
            query_vector=query_vec,
            k=request.k
        )

        # Get full decision point data
        results = []
        for distance, decision_id in zip(distances, decision_ids):
            row = df[df["decision_id"] == decision_id].iloc[0]
            results.append(get_decision_point_response(row, distance))

        search_time_ms = (time.perf_counter() - start_time) * 1000

        return SearchResult(
            query_info={
                "villain_name": request.villain_name,
                "k": request.k,
                "vector_dimension": 99,
            },
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in similarity search: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/search/context", response_model=SearchResult, tags=["Search"])
async def search_by_context(request: ContextSearchRequest):
    """
    Search for decision points by context filters

    Filters decision points by various context parameters and returns matches.
    """
    start_time = time.perf_counter()

    try:
        df = app_state["df"]

        # Validate villain exists
        if request.villain_name not in df["villain_name"].unique():
            raise HTTPException(
                status_code=404,
                detail=f"Villain '{request.villain_name}' not found in dataset"
            )

        # Start with villain filter
        filtered_df = df[df["villain_name"] == request.villain_name].copy()

        # Apply filters
        if request.street:
            filtered_df = filtered_df[filtered_df["street"] == request.street.value]

        if request.position:
            filtered_df = filtered_df[filtered_df["villain_position"] == request.position.value]

        if request.pot_bb_min is not None:
            filtered_df = filtered_df[filtered_df["pot_bb"] >= request.pot_bb_min]

        if request.pot_bb_max is not None:
            filtered_df = filtered_df[filtered_df["pot_bb"] <= request.pot_bb_max]

        if request.spr_min is not None:
            filtered_df = filtered_df[filtered_df["spr"] >= request.spr_min]

        if request.spr_max is not None:
            filtered_df = filtered_df[filtered_df["spr"] <= request.spr_max]

        # Limit to k results
        filtered_df = filtered_df.head(request.k)

        # Convert to response
        results = [get_decision_point_response(row) for _, row in filtered_df.iterrows()]

        search_time_ms = (time.perf_counter() - start_time) * 1000

        return SearchResult(
            query_info={
                "villain_name": request.villain_name,
                "filters": request.dict(exclude={"villain_name", "k"}, exclude_none=True),
                "k": request.k,
            },
            results=results,
            total_results=len(results),
            search_time_ms=search_time_ms,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in context search: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/villains", response_model=VillainsListResponse, tags=["Villains"])
async def list_villains():
    """
    List all indexed villains with summary statistics
    """
    try:
        df = app_state["df"]
        index_builder = app_state["index_builder"]

        villains = []
        for villain_name in df["villain_name"].unique():
            villain_info = get_villain_info(villain_name, df, index_builder)
            villains.append(villain_info)

        # Sort by total decision points (descending)
        villains.sort(key=lambda v: v.total_decision_points, reverse=True)

        return VillainsListResponse(
            total_villains=len(villains),
            villains=villains,
        )

    except Exception as e:
        logger.exception(f"Error listing villains: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/villain/{villain_name}", response_model=VillainInfo, tags=["Villains"])
async def get_villain(villain_name: str):
    """
    Get information about a specific villain
    """
    try:
        df = app_state["df"]

        if villain_name not in df["villain_name"].unique():
            raise HTTPException(
                status_code=404,
                detail=f"Villain '{villain_name}' not found"
            )

        index_builder = app_state["index_builder"]
        return get_villain_info(villain_name, df, index_builder)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting villain: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/villain/{villain_name}/stats", response_model=VillainStatsResponse, tags=["Villains"])
async def get_villain_stats(villain_name: str):
    """
    Get detailed statistics for a specific villain
    """
    try:
        df = app_state["df"]

        if villain_name not in df["villain_name"].unique():
            raise HTTPException(
                status_code=404,
                detail=f"Villain '{villain_name}' not found"
            )

        villain_df = df[df["villain_name"] == villain_name]
        index_builder = app_state["index_builder"]

        # Get basic info
        villain_info = get_villain_info(villain_name, df, index_builder)

        # Action distribution by street
        action_distribution = {}
        for street in ["preflop", "flop", "turn", "river"]:
            street_df = villain_df[villain_df["street"] == street]
            if len(street_df) > 0:
                action_distribution[street] = street_df["villain_action"].value_counts().to_dict()

        # Pot size distribution (buckets)
        pot_buckets = {
            "0-5 BB": len(villain_df[villain_df["pot_bb"] <= 5]),
            "5-10 BB": len(villain_df[(villain_df["pot_bb"] > 5) & (villain_df["pot_bb"] <= 10)]),
            "10-20 BB": len(villain_df[(villain_df["pot_bb"] > 10) & (villain_df["pot_bb"] <= 20)]),
            "20-50 BB": len(villain_df[(villain_df["pot_bb"] > 20) & (villain_df["pot_bb"] <= 50)]),
            "50+ BB": len(villain_df[villain_df["pot_bb"] > 50]),
        }

        # SPR distribution
        spr_buckets = {
            "Low (≤5)": len(villain_df[villain_df["spr"] <= 5]),
            "Medium (5-15)": len(villain_df[(villain_df["spr"] > 5) & (villain_df["spr"] <= 15)]),
            "High (>15)": len(villain_df[villain_df["spr"] > 15]),
        }

        # Position stats
        position_stats = {}
        for position in villain_df["villain_position"].unique():
            pos_df = villain_df[villain_df["villain_position"] == position]
            position_stats[position] = {
                "count": len(pos_df),
                "avg_pot_bb": float(pos_df["pot_bb"].mean()),
                "top_actions": pos_df["villain_action"].value_counts().head(3).to_dict(),
            }

        return VillainStatsResponse(
            villain=villain_info,
            action_distribution=action_distribution,
            pot_size_distribution=pot_buckets,
            spr_distribution=spr_buckets,
            position_stats=position_stats,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting villain stats: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/decision/{decision_id}", response_model=DecisionPointResponse, tags=["Decisions"])
async def get_decision(decision_id: str):
    """
    Get details of a specific decision point
    """
    try:
        df = app_state["df"]

        decision_df = df[df["decision_id"] == decision_id]

        if len(decision_df) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Decision point '{decision_id}' not found"
            )

        row = decision_df.iloc[0]
        return get_decision_point_response(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting decision: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/hand/{hand_id}", response_model=HandHistoryResponse, tags=["Hands"])
async def get_hand_history(hand_id: str):
    """
    Get all decision points for a specific hand
    """
    try:
        df = app_state["df"]

        hand_df = df[df["hand_id"] == hand_id]

        if len(hand_df) == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Hand '{hand_id}' not found"
            )

        # Get villain name from first decision point
        villain_name = hand_df.iloc[0]["villain_name"]

        # Convert all decision points
        decision_points = [get_decision_point_response(row) for _, row in hand_df.iterrows()]

        return HandHistoryResponse(
            hand_id=hand_id,
            villain_name=villain_name,
            decision_points=decision_points,
            total_decision_points=len(decision_points),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting hand history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/search/range-analysis", response_model=RangeAnalysisResponse, tags=["Search"])
async def analyze_range(request: RangeAnalysisRequest):
    """
    Analyze what holdings (hand strength, draws) villain actually had in similar situations

    This endpoint shows the actual cards/holdings a player had when taking specific actions,
    categorized by hand strength, draws, and board texture. Perfect for understanding
    whether a player is betting for value, bluffing, or semi-bluffing.
    """
    start_time = time.perf_counter()

    try:
        from src.api.range_analysis import analyze_range_distribution

        df = app_state["df"]

        # Validate villain exists
        if request.villain_name not in df["villain_name"].unique():
            raise HTTPException(
                status_code=404,
                detail=f"Villain '{request.villain_name}' not found in dataset"
            )

        # Build filters
        filters = {
            'villain_name': request.villain_name,
            'street': request.street.value if request.street else None,
            'position': request.position.value if request.position else None,
            'action': request.action,
            'pot_bb_min': request.pot_bb_min,
            'pot_bb_max': request.pot_bb_max,
        }

        # Perform analysis
        result = analyze_range_distribution(df, filters)

        search_time_ms = (time.perf_counter() - start_time) * 1000
        result['search_time_ms'] = search_time_ms

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in range analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    # Configure logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
