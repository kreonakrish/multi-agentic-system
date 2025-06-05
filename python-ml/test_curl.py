import requests
import json

# Test command
TEST_COMMAND = """Please download and process the Avocado Prices dataset from this GitHub URL:
https://raw.githubusercontent.com/fivethirtyeight/data/master/avocado-prices/avocado.csv

The dataset should contain information about avocado prices and volumes."""

# Prepare the request
endpoint = "http://localhost:5000/api/ml/agent/92/execute_all"
payload = {
    "command": TEST_COMMAND,
    "team_id": 77,
    "conversation_settings_id": 131,
    "end_prompt": "The response should include the downloaded dataset in JSON format"
}

try:
    response = requests.post(endpoint, json=payload)
    response.raise_for_status()
    
    result = response.json()
    print(json.dumps(result, indent=2))
    
except Exception as e:
    print(f"Error: {str(e)}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"Response status code: {e.response.status_code}")
        print(f"Response text: {e.response.text}") 