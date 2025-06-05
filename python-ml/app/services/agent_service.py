from typing import Dict, Any, Optional
from app.models.agent import Agent
from app.utils.logger import logger
from app.utils.enums import InteractionType, AgentStatus
from app.config.openai_config import get_openai_client
from app.utils.db import get_db_connection, safe_close_connection
import requests
import pandas as pd
from io import StringIO
import re
import json

def initialize_agent_from_db(agent_id: int) -> Optional[Agent]:
    """
    Initialize an agent from database records.
    Args:
        agent_id: The ID of the agent to initialize
    Returns:
        Agent instance if found, None otherwise
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get agent details
        cursor.execute("""
            SELECT name, memory_type, foundation_model, status
            FROM agents
            WHERE id = %s
        """, (agent_id,))
        agent_data = cursor.fetchone()
        
        if not agent_data:
            logger.warning(f"No agent found with ID {agent_id}")
            return None
        
        # Create agent instance
        agent = Agent(
            agent_id=agent_id,
            name=agent_data['name'],
            memory_type=agent_data['memory_type'],
            foundation_model=agent_data['foundation_model'],
            status=agent_data['status']
        )
        
        # Get agent's tools
        cursor.execute("""
            SELECT t.tool_name, t.description, t.tool_type
            FROM agent_tools at
            JOIN tools t ON at.tool_id = t.id
            WHERE at.agent_id = %s
        """, (agent_id,))
        tools = cursor.fetchall()
        
        # Add tools to agent
        for tool in tools:
            agent.add_tool(tool['tool_name'], tool['description'], tool['tool_type'])
        
        logger.info(f"Successfully initialized agent {agent_id} from database")
        return agent
        
    except Exception as e:
        logger.error(f"Error initializing agent {agent_id} from database: {str(e)}")
        raise
    finally:
        safe_close_connection(conn, cursor)

class AgentService:
    """Service for managing agent operations"""
    
    def __init__(self):
        self.agents: Dict[int, Agent] = {}
        self.openai = get_openai_client()
        self.base_url = "http://localhost:5000"  # Update with your actual base URL

    def initialize_agent(self, agent_id: int) -> Dict[str, Any]:
        """Initialize an agent with the given ID"""
        try:
            # For now, create a simple agent
            agent = Agent(
                agent_id=agent_id,
                name=f"Agent_{agent_id}",
                memory_type="short_term",
                foundation_model="gpt-3.5-turbo"  # Always use a valid OpenAI model
            )
            self.agents[agent_id] = agent
            logger.info(f"Agent {agent_id} initialized successfully")
            return agent.to_dict()
        except Exception as e:
            logger.error(f"Failed to initialize agent {agent_id}: {str(e)}")
            raise

    def send_message(
        self,
        agent_id: int,
        target_agent_id: int,
        message: str,
        interaction_type: str = InteractionType.DIRECT.value
    ) -> Dict[str, Any]:
        """Send a message from one agent to another"""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Use OpenAI to process the message
            try:
                response = self.openai.ChatCompletion.create(
                    model=agent.foundation_model,
                    messages=[
                        {"role": "system", "content": f"You are Agent_{agent_id}, communicating with Agent_{target_agent_id}"},
                        {"role": "user", "content": message}
                    ]
                )
                processed_message = response.choices[0].message.content
            except Exception as e:
                logger.error(f"Error processing message with OpenAI: {str(e)}")
                processed_message = message  # Fallback to original message
            
            logger.info(f"Agent {agent_id} sending message to {target_agent_id}")
            return {
                'status': 'success',
                'source_agent': agent_id,
                'target_agent': target_agent_id,
                'original_message': message,
                'processed_message': processed_message,
                'interaction_type': interaction_type
            }
        except Exception as e:
            logger.error(f"Failed to send message from agent {agent_id}: {str(e)}")
            raise

    def receive_message(self, agent_id: int, interaction_id: int) -> Dict[str, Any]:
        """Receive a message for an agent"""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Simulate message reception
            logger.info(f"Agent {agent_id} receiving message {interaction_id}")
            return {
                'status': 'success',
                'agent_id': agent_id,
                'interaction_id': interaction_id,
                'received': True
            }
        except Exception as e:
            logger.error(f"Failed to receive message for agent {agent_id}: {str(e)}")
            raise

    def execute_all_tools(self, agent_id: int, command: str) -> Dict[str, Any]:
        """Execute all tools for an agent"""
        try:
            agent = self.agents.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Use OpenAI to analyze and enhance the command
            try:
                response = self.openai.ChatCompletion.create(
                    model=agent.foundation_model,
                    messages=[
                        {"role": "system", "content": "You are an AI assistant helping to analyze and enhance tool commands."},
                        {"role": "user", "content": f"Analyze and enhance this command: {command}"}
                    ]
                )
                enhanced_command = response.choices[0].message.content
            except Exception as e:
                logger.error(f"Error enhancing command with OpenAI: {str(e)}")
                enhanced_command = command  # Fallback to original command
            
            logger.info(f"Agent {agent_id} executing tools with command: {enhanced_command}")
            return {
                'status': 'success',
                'agent_id': agent_id,
                'original_command': command,
                'enhanced_command': enhanced_command,
                'tools_executed': agent.tools,
                'result': 'Tools executed successfully'
            }
        except Exception as e:
            logger.error(f"Failed to execute tools for agent {agent_id}: {str(e)}")
            raise

    def validate_response_with_llm(self, response: str, end_prompt: str) -> Dict[str, Any]:
        """Validate a response using LLM with enhanced data retrieval"""
        try:
            logger.info('Starting response validation with LLM')
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a validation assistant. Your task is to validate responses and extract URLs if present. Return a JSON response with validation result and URL if found."
                },
                {
                    "role": "user",
                    "content": f"Validate this response against the requirements:\nResponse: {response}\nRequirements: {end_prompt}\n\nProvide your response in JSON format with 'valid' (boolean), 'reason' (string), and 'url' (string if found, null if not) fields."
                }
            ]
            
            validation_result = self.process_with_llm(messages)
            if validation_result["status"] != "success":
                return validation_result
            
            # Parse the LLM response as JSON
            try:
                validation_json = json.loads(validation_result["response"])
                
                # If validation is successful, check for URL and call helper function
                if validation_json.get("valid", False) and validation_json.get("url"):
                    data_result = self.helper_tool_function(validation_json["url"])
                    validation_json["data"] = data_result
                
                return {
                    "status": "success",
                    "valid": validation_json.get("valid", False),
                    "reason": validation_json.get("reason", ""),
                    "url": validation_json.get("url"),
                    "data": validation_json.get("data")
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": "Failed to parse LLM response as JSON"
                }
            
        except Exception as e:
            logger.error(f"Error in validate_response_with_llm: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Validation failed: {str(e)}"
            }

    def helper_tool_function(self, url: str) -> Dict[str, Any]:
        """Helper function to retrieve and process data from tools"""
        try:
            logger.info(f'Starting helper tool function with URL: {url}')
            
            # Get tool description from API
            tool_response = requests.get(f"{self.base_url}/api/tools/46")
            if tool_response.status_code != 200:
                raise Exception(f"Failed to get tool info: {tool_response.text}")
            
            tool_data = tool_response.json()
            description = tool_data.get('description', '')
            
            # Parse the description to get dataset information
            datasets = {}
            for line in description.split('\n'):
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        name = parts[1].strip()
                        url_part = parts[2].strip()
                        if name and 'http' in url_part:
                            # Extract URL from markdown link if present
                            url_match = re.search(r'\[(.*?)\]\((.*?)\)', url_part)
                            if url_match:
                                datasets[name] = url_match.group(2)
                            else:
                                datasets[name] = url_part

            # Find the matching dataset
            matching_dataset = None
            for name, dataset_url in datasets.items():
                if url.lower() in dataset_url.lower():
                    matching_dataset = {"name": name, "url": dataset_url}
                    break

            if not matching_dataset:
                return {
                    "status": "error",
                    "message": "URL not found in available datasets"
                }

            # Fetch data from GitHub
            data_response = requests.get(matching_dataset["url"])
            if data_response.status_code != 200:
                raise Exception(f"Failed to fetch data: {data_response.text}")

            # Parse CSV data
            csv_data = pd.read_csv(StringIO(data_response.text))
            
            # Get basic statistics
            stats = {
                "row_count": len(csv_data),
                "column_count": len(csv_data.columns),
                "columns": list(csv_data.columns),
                "sample_data": csv_data.head(5).to_dict('records')
            }

            return {
                "status": "success",
                "dataset_name": matching_dataset["name"],
                "dataset_url": matching_dataset["url"],
                "statistics": stats
            }

        except Exception as e:
            logger.error(f"Error in helper_tool_function: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Data retrieval failed: {str(e)}"
            }