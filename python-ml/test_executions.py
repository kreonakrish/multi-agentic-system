import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:5000/api/ml"

def test_execute_with_tools():
    """Test execute_with_tools endpoint"""
    try:
        endpoint = f"{BASE_URL}/agent/92/execute_all"
        payload = {
            "command": "Get me the latest avocado price trends from the dataset",
            "conversation_settings_id": 131
        }
        
        logger.info("Testing execute_with_tools endpoint")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(endpoint, json=payload)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()
    except Exception as e:
        logger.error(f"Error in execute_with_tools test: {str(e)}")
        return None

def test_execute_team_task():
    """Test execute_team_task endpoint"""
    try:
        endpoint = f"{BASE_URL}/team/execute"
        payload = {
            "team_config": {
                "team_id": 77,
                "name": "Data Analysis Team",
                "description": "Team for analyzing dataset trends",
                "members": [
                    {
                        "agent_id": 1,
                        "priority": 3,
                        "accuracy_threshold": 0.9,
                        "success_rate": 0.95
                    }
                ]
            },
            "task": {
                "description": "Analyze and provide insights from the avocado price dataset",
                "requirements": {
                    "context": {
                        "conversation_settings_id": 131,
                        "tool_id": 46,
                        "conversation_history": []
                    }
                }
            }
        }
        
        logger.info("Testing execute_team_task endpoint")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(endpoint, json=payload)
        
        logger.info(f"Status Code: {response.status_code}")
        logger.info(f"Response: {json.dumps(response.json(), indent=2)}")
        
        return response.json()
    except Exception as e:
        logger.error(f"Error in execute_team_task test: {str(e)}")
        return None

if __name__ == "__main__":
    logger.info("Starting execution tests...")
    
    # Test execute_with_tools
    logger.info("\n=== Testing execute_with_tools ===")
    single_agent_result = test_execute_with_tools()
    
    # Test execute_team_task
    logger.info("\n=== Testing execute_team_task ===")
    team_result = test_execute_team_task()
    
    logger.info("\n=== Test Summary ===")
    logger.info(f"Single Agent Execution: {'Success' if single_agent_result else 'Failed'}")
    logger.info(f"Team Task Execution: {'Success' if team_result else 'Failed'}") 