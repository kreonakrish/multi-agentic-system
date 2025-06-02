import requests
import json
import logging
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API endpoint
API_BASE_URL = "http://localhost:5000/api"

def parse_command_line_args():
    """Parse command line arguments in the format key=value"""
    overrides = {}
    for arg in sys.argv[1:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            overrides[key] = value
    return overrides

def update_nested_dict(d, key, value):
    """Update nested dictionary using dot notation keys"""
    if '.' in key:
        main_key, sub_key = key.split('.', 1)
        if main_key not in d:
            d[main_key] = {}
        update_nested_dict(d[main_key], sub_key, value)
    else:
        d[key] = value

def test_team_execution():
    # Get command line overrides
    overrides = parse_command_line_args()
    logger.info(f"Command line overrides: {overrides}")

    # Template for team task execution
    payload = {
        "team_config": {
            "team_id": "1234567890",
            "name": "PySpark Development Team",
            "description": "Team specialized in PySpark development",
            "members": [
                {
                    "agent_id": 10,  # Using your existing test agent
                    "priority": 3,
                    "accuracy_threshold": 0.9,
                    "success_rate": 0.95,
                    "role": "lead_developer"
                },
                {
                    "agent_id": 11,
                    "priority": 2,
                    "accuracy_threshold": 0.8,
                    "success_rate": 0.9,
                    "role": "code_reviewer"
                }
            ]
        },
        "task": {
            "description": "Write a hello world PySpark code",
            "requirements": {
                "min_accuracy": 0.85,
                "max_time": 1800,  # 30 minutes max
                "specific_tools": ["pyspark"],
                "output_format": "python_code",
                "code_requirements": {
                    "must_include": [
                        "SparkSession",
                        "create simple RDD",
                        "basic transformation",
                        "show output"
                    ],
                    "style_guide": "PEP 8",
                    "comments_required": True
                }
            }
        }
    }

    # Apply overrides
    if 'team_id' in overrides:
        payload['team_config']['team_id'] = overrides['team_id']
    if 'description' in overrides:
        payload['task']['description'] = overrides['description']
    
    # Log the final payload
    logger.info("Final payload after overrides:")
    logger.info(json.dumps(payload, indent=2))

    try:
        # Make the API call
        logger.info("Sending team task execution request...")
        response = requests.post(
            f"{API_BASE_URL}/ml/team/execute",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # Check response
        if response.status_code == 200:
            result = response.json()
            logger.info("Task execution successful!")
            logger.info(f"Team ID: {result['team']['team_id']}")
            logger.info(f"Task Status: {result['result']['final_status']}")
            logger.info("\nFull Response:")
            print(json.dumps(result, indent=2))
            
            # If task completed, check history
            if result['result']['final_status'] == 'completed':
                check_team_history(result['team']['team_id'])
        else:
            logger.error(f"Error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")

def check_team_history(team_id):
    """Check the history of team tasks"""
    try:
        logger.info(f"\nChecking history for team {team_id}...")
        response = requests.get(
            f"{API_BASE_URL}/ml/team/history",
            params={"team_id": team_id, "limit": 5}
        )
        
        if response.status_code == 200:
            history = response.json()
            logger.info("\nRecent team history:")
            print(json.dumps(history, indent=2))
        else:
            logger.error(f"Error getting history: {response.status_code}")
            
    except Exception as e:
        logger.error(f"Error checking history: {str(e)}")

def main():
    logger.info("Starting team task execution test...")
    test_team_execution()

if __name__ == "__main__":
    main() 