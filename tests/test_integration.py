"""
API Integration Tests
Tests all major API endpoints to ensure they work correctly
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("[TEST] Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200, f"Health check failed: {response.status_code}"

    data = response.json()
    assert data["status"] == "healthy", "API not healthy"
    assert "version" in data, "Version missing"
    print(f"[PASS] Health check passed - Version: {data['version']}, Indices: {data['indices_loaded']}, Vectors: {data['total_vectors']}")
    return data

def test_villains():
    """Test villains list endpoint"""
    print("\n[TEST] Testing /villains endpoint...")
    response = requests.get(f"{BASE_URL}/villains")
    assert response.status_code == 200, f"Villains endpoint failed: {response.status_code}"

    data = response.json()
    assert "total_villains" in data, "Missing total_villains"
    assert "villains" in data, "Missing villains list"
    print(f"[PASS] Found {data['total_villains']} villains")

    if data['villains']:
        villain = data['villains'][0]
        print(f"   Top villain: {villain['name']} - {villain['total_decision_points']} decision points")
    return data

def test_villain_detail(villain_name):
    """Test individual villain endpoint"""
    print(f"\n[TEST] Testing /villain/{villain_name} endpoint...")
    response = requests.get(f"{BASE_URL}/villain/{villain_name}")
    assert response.status_code == 200, f"Villain detail failed: {response.status_code}"

    data = response.json()
    assert data["name"] == villain_name, "Villain name mismatch"
    print(f"[PASS] Villain {villain_name} details:")
    print(f"   Decision points: {data['total_decision_points']}")
    print(f"   Indexed vectors: {data['indexed_vectors']}")
    print(f"   Streets: {data['streets']}")
    return data

def test_context_search(villain_name):
    """Test context-based search"""
    print(f"\n[TEST] Testing /search/context endpoint...")

    payload = {
        "villain_name": villain_name,
        "street": "flop",
        "k": 10
    }

    response = requests.post(f"{BASE_URL}/search/context", json=payload)
    assert response.status_code == 200, f"Context search failed: {response.status_code}"

    data = response.json()
    print(f"[PASS] Context search returned {data['total_results']} results in {data['search_time_ms']:.2f}ms")

    if data['results']:
        result = data['results'][0]
        print(f"   First result: {result['street']} - {result['villain_action']} - Pot: {result['pot_bb']} BB")
    return data

def test_range_analysis(villain_name):
    """Test range analysis endpoint"""
    print(f"\n[TEST] Testing /search/range-analysis endpoint...")

    payload = {
        "villain_name": villain_name,
        "street": "flop"
    }

    response = requests.post(f"{BASE_URL}/search/range-analysis", json=payload)
    assert response.status_code == 200, f"Range analysis failed: {response.status_code}"

    data = response.json()
    print(f"[PASS] Range analysis completed in {data['search_time_ms']:.2f}ms")
    print(f"   Total samples: {data['total_samples']}")
    print(f"   Hand strength types: {len(data['hand_strength_distribution'])}")
    print(f"   Draw types: {len(data['draws_distribution'])}")
    print(f"   Examples: {len(data['examples'])}")

    if data['hand_strength_distribution']:
        print("\n   Hand Strength Distribution:")
        for strength, dist in list(data['hand_strength_distribution'].items())[:3]:
            print(f"     {strength}: {dist['count']} ({dist['percentage']}%)")

    return data

def test_villain_stats(villain_name):
    """Test villain stats endpoint"""
    print(f"\n[TEST] Testing /villain/{villain_name}/stats endpoint...")
    response = requests.get(f"{BASE_URL}/villain/{villain_name}/stats")
    assert response.status_code == 200, f"Villain stats failed: {response.status_code}"

    data = response.json()
    print(f"[PASS] Villain stats retrieved")
    print(f"   Action distribution streets: {len(data['action_distribution'])}")
    print(f"   Pot size buckets: {len(data['pot_size_distribution'])}")
    return data

def run_all_tests():
    """Run all API tests"""
    print("=" * 60)
    print("Starting SpinAnalyzer API Tests")
    print("=" * 60)

    start_time = time.time()

    try:
        # Test health
        health_data = test_health()

        # Test villains list
        villains_data = test_villains()

        if villains_data['total_villains'] == 0:
            print("\n[WARN] No villains found in database. Skipping detailed tests.")
            return True

        # Get first villain for testing
        test_villain = villains_data['villains'][0]['name']

        # Test villain detail
        test_villain_detail(test_villain)

        # Test context search
        test_context_search(test_villain)

        # Test range analysis
        test_range_analysis(test_villain)

        # Test villain stats
        test_villain_stats(test_villain)

        elapsed = time.time() - start_time

        print("\n" + "=" * 60)
        print(f"[SUCCESS] ALL TESTS PASSED in {elapsed:.2f}s")
        print("=" * 60)
        return True

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n[FAIL] Cannot connect to API at {BASE_URL}")
        print("   Make sure the API server is running: python run_api.py")
        return False
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
