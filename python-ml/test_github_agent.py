import requests
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('github_agent_test.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:5000/api"

# Test command
TEST_COMMAND = """Please download and process the Avocado Prices dataset from this GitHub URL:
https://raw.githubusercontent.com/fivethirtyeight/data/master/avocado-prices/avocado.csv

The dataset should contain information about avocado prices and volumes."""

def test_execute_with_tools():
    """Test GitHub Agent using execute_with_tools endpoint"""
    logger.info("Testing execute_with_tools for GitHub Agent...")
    
    # Prepare the request
    endpoint = f"{API_BASE_URL}/ml/agent/92/execute_all"
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
        logger.info("Execute with tools response:")
        print(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error in execute_with_tools: {str(e)}")
        return None

def test_execute_team_task():
    """Test GitHub Agent using execute_team_task endpoint"""
    logger.info("Testing execute_team_task for GitHub Agent...")
    
    # Prepare the request
    endpoint = f"{API_BASE_URL}/ml/team/execute"
    payload = {
        "team_config": {
            "team_id": 77,
            "name": "GitHub Data Team",
            "description": "Team for downloading and processing GitHub datasets",
            "members": [
                {
                    "agent_id": 92,
                    "priority": 1,
                    "accuracy_threshold": 0.8,
                    "success_rate": 0.9,
                    "role": "github_data_provider"
                }
            ]
        },
        "task": {
            "description": TEST_COMMAND,
            "requirements": {
                "min_accuracy": 0.8,
                "min_success_rate": 0.8,
                "end_prompt": "The response should include the downloaded dataset in JSON format"
            }
        },
        "conversation_settings_id": 131
    }
    
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        
        result = response.json()
        logger.info("Execute team task response:")
        print(json.dumps(result, indent=2))
        
        return result
        
    except Exception as e:
        logger.error(f"Error in execute_team_task: {str(e)}")
        return None

def main():
    """Run all tests"""
    logger.info("Starting GitHub Agent tests...")
    
    # Test execute_with_tools
    tools_result = test_execute_with_tools()
    if tools_result:
        logger.info("Execute with tools test completed successfully")
        
        # Check if we got GitHub data
        validation_results = tools_result.get('validation_results', [])
        if validation_results and any(r.get('github_data') for r in validation_results):
            logger.info("Successfully retrieved GitHub data!")
        else:
            logger.warning("No GitHub data found in the response")
    else:
        logger.error("Execute with tools test failed")
    
    # Test execute_team_task
    team_result = test_execute_team_task()
    if team_result:
        logger.info("Execute team task test completed successfully")
        
        # Check team execution results
        result = team_result.get('result', {})
        if result.get('final_status') == 'completed':
            logger.info("Team task completed successfully!")
            
            # Check for GitHub data in results
            results = result.get('results', [])
            for r in results:
                if r.get('result', {}).get('validation_results'):
                    logger.info("Found validation results with GitHub data!")
        else:
            logger.warning("Team task did not complete successfully")
    else:
        logger.error("Execute team task test failed")
    
    logger.info("All tests completed")

if __name__ == "__main__":
    main() 