import requests
import json
import logging
import argparse
from typing import Dict, Any, Optional
import os
from datetime import datetime
import time

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DEFAULT_MESSAGE_TEMPLATE = """
# You are part of Team {team_id} to complete execution of any task.
# You are an intelligent agent named Databricks Agent {agent_id}. 

# The agent memory is created with both types:
agent_memory = {{
    'SHORT_TERM_MEMORY': {{
        'start_prompt': 'You are a Databricks Agent and know Spark very well',
        'end_prompt': 'Have a Unit Test to verify your code'
    }},
    'LONG_TERM_MEMORY': {{
        'context': 'Apache Spark & Databricks best practices'
    }}
}}

# Tools added to agent's tools list {tool_ids}:
{tool_details}

User's request: "{user_request}"

Considering the provided context, determine which tool(s) should be utilized and provide structured instructions for execution.
# If execution needs multiple steps, send instructions.
# Leverage workflow service if needed.
"""

class AgentExecutor:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        logger.info(f"Initialized AgentExecutor with base URL: {base_url}")
    
    def initialize_agent(self, agent_id: int, name: str, memory_type: str, foundation_model: str) -> Dict[str, Any]:
        """Initialize an agent with given parameters"""
        try:
            url = f"{self.base_url}/api/ml/agent/{agent_id}/initialize"
            payload = {
                "name": name,
                "memory_type": memory_type,
                "foundation_model": foundation_model,
                "use_prod": False
            }
            logger.info(f"Initializing agent {agent_id} with payload: {payload}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Agent initialization response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error initializing agent: {str(e)}")
            raise

    def create_agent_memory(self, agent_id: int, memory_type: str, start_prompt: Optional[str] = None,
                          end_prompt: Optional[str] = None, context: Optional[str] = None) -> Dict[str, Any]:
        """Create memory for an agent"""
        try:
            url = f"{self.base_url}/api/ml/agent-memory"
            payload = {
                "agent_id": agent_id,
                "memory_type": memory_type,
                "start_prompt": start_prompt,
                "end_prompt": end_prompt,
                "context": context
            }
            logger.info(f"Creating agent memory with payload: {payload}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Memory creation response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating agent memory: {str(e)}")
            raise

    def add_tool_to_agent(self, agent_id: int, tool_ids: list[int], team_id: int) -> Dict[str, Any]:
        """Add tools to an agent"""
        try:
            url = f"{self.base_url}/api/ml/agent/{agent_id}/tools"
            payload = {
                "tool_ids": tool_ids,
                "team_id": team_id
            }
            logger.info(f"Adding tools {tool_ids} to agent {agent_id}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tool addition response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding tools to agent: {str(e)}")
            raise

    def get_tool_details(self, tool_id: int) -> Dict[str, Any]:
        """Get tool details by ID"""
        try:
            url = f"{self.base_url}/api/tools/{tool_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting tool details: {str(e)}")
            return {
                "tool_name": f"Tool {tool_id}",
                "tool_type": "Unknown",
                "hostname": "unknown",
                "auth_method": "unknown"
            }

    def send_message_to_agent(self, agent_id: int, message: str, team_id: int) -> Dict[str, Any]:
        """Send a message to an agent and wait for response"""
        try:
            # Send the message
            url = f"{self.base_url}/api/ml/agent/{agent_id}/send"
            payload = {
                "message": message,
                "interaction_type": "direct",
                "team_id": team_id
            }
            logger.info(f"Sending message to agent {agent_id} with payload: {payload}")
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            initial_response = response.json()
            logger.info(f"Initial message response: {initial_response}")
            
            if initial_response.get('status') != 'success':
                raise Exception(f"Failed to send message: {initial_response}")
            
            # If we have a model response already, return it
            if 'model_response' in initial_response:
                logger.info("Received immediate model response")
                return initial_response
            
            # Get the conversation ID from the response
            conversation_id = initial_response.get('conversation_id')
            if not conversation_id:
                raise Exception("No conversation ID received in response")
            
            # Poll for the model's response
            logger.info("Waiting for model response...")
            max_retries = 30  # Maximum number of retries (5 minutes with 10-second intervals)
            retry_count = 0
            
            while retry_count < max_retries:
                # Get the latest response
                response_url = f"{self.base_url}/api/ml/agent/{agent_id}/response/{conversation_id}"
                logger.info(f"Polling for response at: {response_url}")
                response = self.session.get(response_url)
                response.raise_for_status()
                response_data = response.json()
                logger.info(f"Poll response: {response_data}")
                
                # Check if we have a model response
                if response_data.get('model_response'):
                    logger.info("Received model response!")
                    return response_data
                
                # Wait before next retry
                time.sleep(10)
                retry_count += 1
                logger.info(f"Waiting for response... (attempt {retry_count}/{max_retries})")
            
            raise Exception("Timeout waiting for model response")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error in message communication: {str(e)}")
            raise

def format_tool_details(executor: AgentExecutor, tool_ids: list[int]) -> str:
    """Format tool details for the message"""
    tool_details = []
    for tool_id in tool_ids:
        tool = executor.get_tool_details(tool_id)
        tool_details.append(f"""dbx_tool_{tool_id} = {{
    'tool_name': '{tool["tool_name"]}',
    'tool_type': '{tool["tool_type"]}',
    'hostname': '{tool["hostname"]}',
    'auth_method': '{tool["auth_method"]}'
}}""")
    return "\n".join(tool_details)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Execute agent operations')
    parser.add_argument('agent_id', type=int, help='ID of the agent to work with')
    parser.add_argument('tool_ids', type=int, nargs='+', help='List of tool IDs to associate with the agent')
    parser.add_argument('team_id', type=int, help='Team ID the agent is associated with')
    parser.add_argument('--user-request', type=str, default="How to build a python based databricks spark code?",
                      help='The user request to process')
    parser.add_argument('--message-file', type=str, help='Path to a file containing a custom message template')
    args = parser.parse_args()

    logger.info(f"Starting execution with arguments: {args}")

    # Initialize the executor
    executor = AgentExecutor()

    try:
        # Initialize the agent
        logger.info("Initializing Databricks Agent...")
        agent_init = executor.initialize_agent(
            agent_id=args.agent_id,
            name="Databricks Agent",
            memory_type="SHORT_TERM_MEMORY",
            foundation_model="gpt-4"
        )
        logger.info(f"Agent initialized: {agent_init}")

        # Create SHORT_TERM_MEMORY
        logger.info("Creating SHORT_TERM_MEMORY...")
        short_term = executor.create_agent_memory(
            agent_id=args.agent_id,
            memory_type="SHORT_TERM_MEMORY",
            start_prompt="You are a Databricks Agent and know Spark very well",
            end_prompt="Have a Unit Test to verify your code"
        )
        logger.info(f"SHORT_TERM_MEMORY created: {short_term}")

        # Create LONG_TERM_MEMORY
        logger.info("Creating LONG_TERM_MEMORY...")
        long_term = executor.create_agent_memory(
            agent_id=args.agent_id,
            memory_type="LONG_TERM_MEMORY",
            context="Apache Spark & Databricks best practices"
        )
        logger.info(f"LONG_TERM_MEMORY created: {long_term}")

        # Add tools to agent
        logger.info(f"Adding tools {args.tool_ids} to agent...")
        tools_response = executor.add_tool_to_agent(
            agent_id=args.agent_id,
            tool_ids=args.tool_ids,
            team_id=args.team_id
        )
        logger.info(f"Tools added: {tools_response}")

        # Prepare message
        if args.message_file and os.path.exists(args.message_file):
            with open(args.message_file, 'r') as f:
                message_template = f.read()
        else:
            message_template = DEFAULT_MESSAGE_TEMPLATE

        # Format tool details
        tool_details = format_tool_details(executor, args.tool_ids)

        # Format the message
        message = message_template.format(
            team_id=args.team_id,
            agent_id=args.agent_id,
            tool_ids=args.tool_ids,
            tool_details=tool_details,
            user_request=args.user_request
        )

        # Send the message and wait for response
        logger.info("Sending message to agent...")
        logger.info(f"Message content:\n{message}")
        message_response = executor.send_message_to_agent(
            agent_id=args.agent_id,
            message=message,
            team_id=args.team_id
        )
        
        # Display the model's response
        if message_response.get('model_response'):
            logger.info("\nModel Response:")
            logger.info("=" * 80)
            logger.info(message_response['model_response'])
            logger.info("=" * 80)
        else:
            logger.warning("No model response received")
            logger.info("Full response:")
            logger.info(json.dumps(message_response, indent=2))

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 