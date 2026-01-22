#!/usr/bin/env python3
"""
MCP Server Plan - Integration Tests

Tests for:
1. ToolClassifier - 3-stage tool selection
2. IdempotencyService - Request deduplication
3. ToolEventsService - Real-time events
4. Application ID Filtering - Multi-app support

Usage:
    # Start the bridge server first:
    cd /home/ahmet/MetisAgent/MetisAgent3
    python bridge_server.py

    # Then run tests:
    python tests/test_mcp_server.py
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5001"
HEADERS = {"Content-Type": "application/json"}


def print_header(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name: str, success: bool, details: str = ""):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"       {details}")


def test_server_health():
    """Test if server is running"""
    print_header("1. Server Health Check")
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        success = response.status_code == 200
        print_result("Server Health", success, f"Status: {response.status_code}")
        return success
    except requests.exceptions.ConnectionError:
        print_result("Server Health", False, "Connection refused - is the server running?")
        return False


def test_classifier_stats():
    """Test classifier statistics endpoint"""
    print_header("2. Tool Classifier Statistics")
    try:
        response = requests.get(f"{BASE_URL}/api/tools/classifier/stats", timeout=10)
        data = response.json()

        success = data.get("success", False)
        stats = data.get("statistics", {})

        print_result("Classifier Stats Endpoint", success)

        if success:
            print(f"\n   Indexed: {stats.get('indexed', False)}")
            print(f"   Total Tools: {stats.get('total_tools', 0)}")
            print(f"   Total Capabilities: {stats.get('total_capabilities', 0)}")
            print(f"   Shortlist Size: {stats.get('shortlist_size', 0)}")

            # Category breakdown
            category_counts = stats.get("category_counts", {})
            if category_counts:
                print("\n   Category Breakdown:")
                for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
                    if count > 0:
                        print(f"     - {cat}: {count} tools")

        return success
    except Exception as e:
        print_result("Classifier Stats Endpoint", False, str(e))
        return False


def test_tool_classification():
    """Test tool classification with various queries"""
    print_header("3. Tool Classification Tests")

    test_queries = [
        {
            "query": "SCADA ekranındaki sıcaklık değerini göster",
            "expected_categories": ["scada", "monitoring"],
            "description": "SCADA temperature query"
        },
        {
            "query": "Yeni bir iş emri oluştur",
            "expected_categories": ["workorder", "maintenance"],
            "description": "Work order creation"
        },
        {
            "query": "Alarm listesini getir ve kritik alarmları filtrele",
            "expected_categories": ["alarm", "monitoring"],
            "description": "Alarm filtering"
        },
        {
            "query": "OEE raporunu çalıştır ve üretim verilerini analiz et",
            "expected_categories": ["oee", "datascience", "mes"],
            "description": "OEE analysis"
        },
        {
            "query": "Python kodu yazıp çalıştır",
            "expected_categories": ["code", "computer"],
            "description": "Code execution (high-risk)"
        },
        {
            "query": "Enerji tüketim verilerini analiz et",
            "expected_categories": ["energy", "datascience"],
            "description": "Energy analysis"
        }
    ]

    all_passed = True
    category_matches = 0
    total_tests = len(test_queries)

    for test in test_queries:
        try:
            response = requests.post(
                f"{BASE_URL}/api/tools/classify",
                headers=HEADERS,
                json={"query": test["query"], "include_high_risk": True},
                timeout=10
            )
            data = response.json()

            success = data.get("success", False)
            classification = data.get("classification", {})

            primary_cat = classification.get("primary_category", "unknown")
            tool_names = classification.get("tool_names", [])
            high_risk = classification.get("high_risk_detected", False)
            time_ms = classification.get("classification_time_ms", 0)

            # Check if expected category is detected
            category_match = primary_cat in test["expected_categories"]
            if category_match:
                category_matches += 1

            # Success if API works and category matches (tools may be empty for some categories)
            test_passed = success and category_match

            print_result(
                test["description"],
                test_passed,
                f"Category: {primary_cat}, Tools: {len(tool_names)}, Time: {time_ms:.1f}ms"
            )

            if tool_names:
                print(f"       Shortlisted: {', '.join(tool_names[:5])}")
            elif category_match:
                print(f"       (No tools in '{primary_cat}' category)")

            if high_risk:
                print(f"       ⚠️ High-risk tools detected")

            if not category_match:
                print(f"       Note: Expected {test['expected_categories']}, got {primary_cat}")
                all_passed = False

        except Exception as e:
            print_result(test["description"], False, str(e))
            all_passed = False

    print(f"\n   Category Detection Accuracy: {category_matches}/{total_tests}")

    return all_passed


def test_idempotency_stats():
    """Test idempotency service statistics"""
    print_header("4. Idempotency Service Statistics")
    try:
        response = requests.get(f"{BASE_URL}/api/services/idempotency/stats", timeout=10)
        data = response.json()

        success = data.get("success", False)
        stats = data.get("statistics", {})

        print_result("Idempotency Stats Endpoint", success)

        if success:
            print(f"\n   Total Requests: {stats.get('total_requests', 0)}")
            print(f"   Cache Hits: {stats.get('cache_hits', 0)}")
            print(f"   Cache Misses: {stats.get('cache_misses', 0)}")
            print(f"   Hit Rate: {stats.get('cache_hit_rate', 0):.2%}")
            print(f"   Current Records: {stats.get('current_records', 0)}")
            print(f"   In-Progress: {stats.get('in_progress_requests', 0)}")

        return success
    except Exception as e:
        print_result("Idempotency Stats Endpoint", False, str(e))
        return False


def test_available_tools():
    """Test available tools endpoint and verify application filtering"""
    print_header("5. Available Tools (Application Filtering)")
    try:
        response = requests.get(f"{BASE_URL}/api/tools/available", timeout=10)
        data = response.json()

        success = data.get("success", False)
        tools_data = data.get("tools", {})
        count = data.get("count", 0)

        print_result("Available Tools Endpoint", success, f"Count: {count}")

        if success and tools_data:
            # tools_data is a dict {tool_name: tool_info}
            tool_names = list(tools_data.keys())

            # Group by tool prefix
            axis_tools = [name for name in tool_names if name.startswith("axis_")]
            rmms_tools = [name for name in tool_names if name.startswith("rmms_")]
            other_tools = [name for name in tool_names if not name.startswith(("axis_", "rmms_"))]

            print(f"\n   Axis Tools: {len(axis_tools)}")
            print(f"   RMMS Tools: {len(rmms_tools)}")
            print(f"   Global Tools: {len(other_tools)}")

            # List tools by category
            if axis_tools:
                print(f"\n   Axis: {', '.join(axis_tools[:5])}")
            if rmms_tools:
                print(f"   RMMS: {', '.join(rmms_tools[:5])}")
            if other_tools:
                print(f"   Global: {', '.join(other_tools[:5])}")

        return success
    except Exception as e:
        print_result("Available Tools Endpoint", False, str(e))
        return False


def test_classification_performance():
    """Test classification performance with multiple queries"""
    print_header("6. Classification Performance Test")

    queries = [
        "alarm listesi",
        "iş emri oluştur",
        "SCADA değerlerini göster",
        "enerji raporu",
        "kalite kontrol",
        "üretim verileri",
        "bakım planla",
        "sensör değeri yaz",
        "trend analizi",
        "OEE hesapla"
    ]

    times = []

    for query in queries:
        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/api/tools/classify",
                headers=HEADERS,
                json={"query": query},
                timeout=10
            )
            elapsed = (time.time() - start) * 1000

            data = response.json()
            if data.get("success"):
                internal_time = data.get("classification", {}).get("classification_time_ms", 0)
                times.append(internal_time)
        except:
            pass

    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"   Queries tested: {len(times)}")
        print(f"   Average time: {avg_time:.2f}ms")
        print(f"   Min time: {min_time:.2f}ms")
        print(f"   Max time: {max_time:.2f}ms")

        success = avg_time < 100  # Should be under 100ms
        print_result("Performance", success, f"Target: <100ms, Actual: {avg_time:.2f}ms")
        return success
    else:
        print_result("Performance", False, "No successful classifications")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("   MCP Server Plan - Integration Tests")
    print("   " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*60)

    results = {}

    # 1. Health check
    results["health"] = test_server_health()
    if not results["health"]:
        print("\n❌ Server is not running. Start it with:")
        print("   cd /home/ahmet/MetisAgent/MetisAgent3")
        print("   python bridge_server.py")
        return results

    # 2. Classifier stats
    results["classifier_stats"] = test_classifier_stats()

    # 3. Tool classification
    results["classification"] = test_tool_classification()

    # 4. Idempotency stats
    results["idempotency"] = test_idempotency_stats()

    # 5. Available tools
    results["available_tools"] = test_available_tools()

    # 6. Performance
    results["performance"] = test_classification_performance()

    # Summary
    print_header("Test Summary")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"   Passed: {passed}/{total}")
    print(f"   Failed: {total - passed}/{total}")

    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"   {status} {name}")

    return results


if __name__ == "__main__":
    results = run_all_tests()

    # Exit with error code if any test failed
    if not all(results.values()):
        sys.exit(1)
