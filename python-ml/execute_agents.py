import requests
import json
import logging
from typing import Dict, Any, Optional
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AgentExecutor:
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def initialize_agent(self, agent_id: int, name: str, memory_type: str, foundation_model: str) -> Dict[str, Any]:
        """Initialize an agent with given parameters"""
        try:
            url = f"{self.base_url}/api/ml/agent/{agent_id}/initialize"
            payload = {
                "name": name,
                "memory_type": memory_type,
                "foundation_model": foundation_model
            }
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
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
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating agent memory: {str(e)}")
            raise

    def add_tool_to_agent(self, agent_id: int, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a tool to an agent"""
        try:
            url = f"{self.base_url}/api/ml/agent/{agent_id}/tools"
            response = self.session.post(url, json=tool_data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error adding tool to agent: {str(e)}")
            raise

    def send_message_to_agent(self, agent_id: int, message: str) -> Dict[str, Any]:
        """Send a message to an agent"""
        try:
            url = f"{self.base_url}/api/ml/agent/{agent_id}/send"
            payload = {
                "message": message,
                "interaction_type": "direct"
            }
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending message to agent: {str(e)}")
            raise

def main():
    # Initialize the executor
    executor = AgentExecutor()
    agent_id = 1  # Example agent ID

    try:
        # Initialize the agent
        logger.info("Initializing Databricks Agent...")
        agent_init = executor.initialize_agent(
            agent_id=agent_id,
            name="Databricks Agent",
            memory_type="SHORT_TERM_MEMORY",
            foundation_model="gpt-4"
        )
        logger.info(f"Agent initialized: {agent_init}")

        # Create SHORT_TERM_MEMORY
        logger.info("Creating SHORT_TERM_MEMORY...")
        short_term = executor.create_agent_memory(
            agent_id=agent_id,
            memory_type="SHORT_TERM_MEMORY",
            start_prompt="You are a Databricks Agent and know Spark very well",
            end_prompt="Have a Unit Test to verify your code",
            context=None
        )
        logger.info(f"SHORT_TERM_MEMORY created: {short_term}")

        # Create LONG_TERM_MEMORY
        logger.info("Creating LONG_TERM_MEMORY...")
        long_term = executor.create_agent_memory(
            agent_id=agent_id,
            memory_type="LONG_TERM_MEMORY",
            context="Apache Spark & Databricks best practices"
        )
        logger.info(f"LONG_TERM_MEMORY created: {long_term}")

        # Add DBX Tool
        logger.info("Adding DBX Tool to agent...")
        dbx_tool = executor.add_tool_to_agent(
            agent_id=agent_id,
            tool_data={
                "tool_name": "DBX Tool",
                "tool_type": "WebService",
                "hostname": "databricks.example.com",
                "auth_method": "token"
            }
        )
        logger.info(f"DBX Tool added: {dbx_tool}")

        # Send message to agent
        message = """
You are an intelligent agent named Databricks Agent. 

# The agent memory is created with both types:
agent_memory = {
    'SHORT_TERM_MEMORY': {
        'start_prompt': 'You are a Databricks Agent and know Spark very well',
        'end_prompt': 'Have a Unit Test to verify your code',
        'context': None
    },
    'LONG_TERM_MEMORY': {
        'context': 'Apache Spark & Databricks best practices'
    }
}

# DBX Tool is added to agent's tools list:
dbx_tool = {
    'tool_name': 'DBX Tool',
    'tool_type': 'WebService',
    'hostname': 'databricks.example.com',
    'auth_method': 'token'
}
#Tools: DBX Tool [You only have return message to calling service that DBX Tool was used.]

User's request: "How to build a python based databricks spark code?"

Considering the provided context, determine which tool(s) should be utilized and provide structured instructions for execution.
# If execution needs multiple steps, send instructions.
# Leverage workflow service if needed.
"""
        logger.info("Sending message to agent...")
        response = executor.send_message_to_agent(agent_id=agent_id, message=message)
        logger.info(f"Agent response: {json.dumps(response, indent=2)}")

    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        raise

if __name__ == "__main__":
    main() 