from typing import Dict, Any, Optional
from app.models.agent import Agent
from app.utils.logger import logger
from app.utils.enums import InteractionType, AgentStatus
from app.config.openai_config import get_openai_client
from app.utils.db import get_db_connection, safe_close_connection

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
        
        # Get agent details with team info
        cursor.execute("""
            SELECT a.name, a.memory_type, a.foundation_model, ta.team_id
            FROM agents a
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            WHERE a.id = %s
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
            team_id=agent_data.get('team_id')  # Use get() to handle None case
        )
        
        # Get agent's tools
        cursor.execute("""
            SELECT t.id, t.tool_name, t.description, t.tool_type, t.hostname, t.username, t.auth_method
            FROM agent_tools at
            JOIN tools t ON at.tool_id = t.id
            WHERE at.agent_id = %s
        """, (agent_id,))
        tools = cursor.fetchall()
        
        # Add tools to agent
        for tool in tools:
            agent.add_tool(
                tool_id=tool['id'],
                tool_name=tool['tool_name'],
                tool_type=tool['tool_type'],
                hostname=tool['hostname'],
                username=tool['username'],
                auth_method=tool['auth_method'],
                description=tool['description']
            )
        
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
                response = self.openai.chat.completions.create(
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
            # Initialize agent from database
            agent = initialize_agent_from_db(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            # Execute command with all tools
            logger.info(f"Agent {agent_id} executing tools with command: {command}")
            result = agent.execute_with_tools(command)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute tools for agent {agent_id}: {str(e)}")
            raise 