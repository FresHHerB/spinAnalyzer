"""
API Tests - SpinAnalyzer v2.0
Tests for FastAPI endpoints
"""

import sys
from pathlib import Path
import pytest
from httpx import AsyncClient
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.main import app


@pytest.mark.asyncio
async def test_root():
    """Test root endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["version"] == "2.0.0"


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert "indices_loaded" in data
        assert "total_vectors" in data
        assert "uptime_seconds" in data


@pytest.mark.asyncio
async def test_list_villains():
    """Test villains list endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/villains")
        assert response.status_code == 200
        data = response.json()
        assert "total_villains" in data
        assert "villains" in data
        assert data["total_villains"] > 0
        assert len(data["villains"]) == data["total_villains"]

        # Check villain structure
        villain = data["villains"][0]
        assert "name" in villain
        assert "total_decision_points" in villain
        assert "indexed_vectors" in villain
        assert "streets" in villain
        assert "positions" in villain


@pytest.mark.asyncio
async def test_get_villain():
    """Test get specific villain endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First get list of villains
        villains_response = await client.get("/villains")
        villains = villains_response.json()["villains"]
        villain_name = villains[0]["name"]

        # Get specific villain
        response = await client.get(f"/villain/{villain_name}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == villain_name
        assert "total_decision_points" in data
        assert "avg_pot_bb" in data


@pytest.mark.asyncio
async def test_get_villain_not_found():
    """Test get non-existent villain"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/villain/NonExistentVillain123")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_villain_stats():
    """Test get villain statistics endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # First get a villain name
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        # Get stats
        response = await client.get(f"/villain/{villain_name}/stats")
        assert response.status_code == 200
        data = response.json()
        assert "villain" in data
        assert "action_distribution" in data
        assert "pot_size_distribution" in data
        assert "spr_distribution" in data
        assert "position_stats" in data


@pytest.mark.asyncio
async def test_similarity_search():
    """Test similarity search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get a villain name
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        # Create random query vector (99 dimensions)
        query_vector = np.random.randn(99).tolist()

        # Search
        response = await client.post(
            "/search/similarity",
            json={
                "villain_name": villain_name,
                "query_vector": query_vector,
                "k": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data
        assert "search_time_ms" in data
        assert len(data["results"]) <= 5

        # Check result structure
        if len(data["results"]) > 0:
            result = data["results"][0]
            assert "decision_id" in result
            assert "villain_name" in result
            assert "distance" in result
            assert result["villain_name"] == villain_name


@pytest.mark.asyncio
async def test_similarity_search_invalid_dimension():
    """Test similarity search with invalid vector dimension"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        # Wrong dimension (should be 99)
        query_vector = np.random.randn(50).tolist()

        response = await client.post(
            "/search/similarity",
            json={
                "villain_name": villain_name,
                "query_vector": query_vector,
                "k": 5
            }
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_context_search():
    """Test context-based search endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        # Search by context
        response = await client.post(
            "/search/context",
            json={
                "villain_name": villain_name,
                "street": "preflop",
                "position": "BTN",
                "k": 10
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data

        # Check filters were applied
        for result in data["results"]:
            assert result["street"] == "preflop"
            assert result["villain_position"] == "BTN"


@pytest.mark.asyncio
async def test_get_decision():
    """Test get decision point endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get a decision ID from search
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        search_response = await client.post(
            "/search/context",
            json={"villain_name": villain_name, "k": 1}
        )
        decision_id = search_response.json()["results"][0]["decision_id"]

        # Get decision
        response = await client.get(f"/decision/{decision_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["decision_id"] == decision_id
        assert "villain_name" in data
        assert "street" in data


@pytest.mark.asyncio
async def test_get_decision_not_found():
    """Test get non-existent decision"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/decision/non_existent_id_12345")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_hand_history():
    """Test get hand history endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Get a hand ID from search
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        search_response = await client.post(
            "/search/context",
            json={"villain_name": villain_name, "k": 1}
        )
        hand_id = search_response.json()["results"][0]["hand_id"]

        # Get hand history
        response = await client.get(f"/hand/{hand_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["hand_id"] == hand_id
        assert "decision_points" in data
        assert "total_decision_points" in data
        assert len(data["decision_points"]) == data["total_decision_points"]


@pytest.mark.asyncio
async def test_performance_search():
    """Test search performance is within acceptable limits"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        villains_response = await client.get("/villains")
        villain_name = villains_response.json()["villains"][0]["name"]

        query_vector = np.random.randn(99).tolist()

        response = await client.post(
            "/search/similarity",
            json={
                "villain_name": villain_name,
                "query_vector": query_vector,
                "k": 10
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Search should be fast (<100ms target, typically <10ms)
        assert data["search_time_ms"] < 100, f"Search took {data['search_time_ms']}ms, expected <100ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
