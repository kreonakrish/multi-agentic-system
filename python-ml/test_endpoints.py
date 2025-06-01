import requests
import json
import time
from datetime import datetime

BASE_URL = 'http://localhost:5000/api/ml'

def test_endpoint(method, endpoint, data=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    print(f"\nTesting {method} {endpoint}")
    print("Request:", data if data else "No data")
    
    try:
        if method == 'GET':
            response = requests.get(url, params=params)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        
        print(f"Status Code: {response.status_code}")
        print("Response:", json.dumps(response.json(), indent=2))
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def run_tests():
    success_count = 0
    total_tests = 0

    print("Starting API Tests...")
    print("=" * 50)

    # Test 1: Initialize Agent
    total_tests += 1
    test_data = {"use_prod": False}
    if test_endpoint('POST', '/agent/10/initialize', test_data):
        success_count += 1

    # Test 2: Send Message
    total_tests += 1
    test_data = {
        "target_agent_id": 11,
        "message": "Test message",
        "interaction_type": "direct"
    }
    if test_endpoint('POST', '/agent/10/send', test_data):
        success_count += 1

    # Test 3: Receive Message
    total_tests += 1
    if test_endpoint('POST', '/agent/11/receive/1'):
        success_count += 1

    # Test 4: Start Workflow
    total_tests += 1
    test_data = {
        "type": "sequential",
        "agents": [11, 13, 14],
        "message": "Test workflow"
    }
    if test_endpoint('POST', '/agent/10/workflow', test_data):
        success_count += 1

    # Test 5: Execute All Tools
    total_tests += 1
    test_data = {
        "command": "Test command"
    }
    if test_endpoint('POST', '/agent/10/execute_all', test_data):
        success_count += 1

    # Test 6: Get Team Configuration
    total_tests += 1
    if test_endpoint('GET', '/team/1/config'):
        success_count += 1

    # Test 7: Update Team Configuration
    total_tests += 1
    test_data = {
        "config": {
            "max_concurrent_agents": 5,
            "default_model": "gpt-4"
        },
        "permissions": [
            {"tool_id": 5, "level": "write"},
            {"tool_id": 6, "level": "read"}
        ]
    }
    if test_endpoint('PUT', '/team/1/config', test_data):
        success_count += 1

    # Test 8: Get Team Metrics
    total_tests += 1
    if test_endpoint('GET', '/team/1/metrics', params={"time_range": "24h"}):
        success_count += 1

    print("\n" + "=" * 50)
    print(f"Tests completed: {success_count}/{total_tests} successful")
    print(f"Success rate: {(success_count/total_tests)*100:.2f}%")

if __name__ == "__main__":
    # Wait for server to start
    print("Waiting for server to start...")
    time.sleep(2)
    run_tests() 