from typing import Dict, Any, List, Optional, NamedTuple
from datetime import datetime
from app.utils.enums import AgentStatus
from app.utils.logger import logger
from app.config.openai_config import get_openai_client

class Tool(NamedTuple):
    """Data structure for agent tools"""
    name: str
    description: Optional[str]
    type: str

class Agent:
    """Data model for an agent"""
    
    def __init__(
        self,
        agent_id: int,
        name: str,
        memory_type: str,
        foundation_model: str,
        team_id: Optional[int] = None,
        status: str = AgentStatus.IDLE.value,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.memory_type = memory_type
        self.foundation_model = foundation_model
        self.team_id = team_id
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.tools: List[Tool] = []  # List of Tool objects
        self.metrics: Dict[str, Any] = {
            'total_interactions': 0,
            'successful_interactions': 0,
            'failed_interactions': 0,
            'average_response_time': 0.0
        }
        self._openai = None  # Lazy-loaded OpenAI client

    def get_openai_client(self):
        """Get or initialize OpenAI client"""
        if self._openai is None:
            self._openai = get_openai_client()
        return self._openai

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'memory_type': self.memory_type,
            'foundation_model': self.foundation_model,
            'team_id': self.team_id,
            'status': self.status,
            'tools': [{'name': t.name, 'description': t.description, 'type': t.type} for t in self.tools],
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        """Create an agent instance from dictionary data"""
        try:
            agent = cls(
                agent_id=data['agent_id'],
                name=data['name'],
                memory_type=data['memory_type'],
                foundation_model=data['foundation_model'],
                team_id=data.get('team_id'),
                status=data.get('status', AgentStatus.IDLE.value),
                created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
                updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else None
            )
            # Convert tool dictionaries to Tool objects
            for tool_data in data.get('tools', []):
                agent.add_tool(tool_data['name'], tool_data['description'], tool_data['type'])
            agent.metrics = data.get('metrics', {})
            return agent
        except Exception as e:
            logger.error(f"Error creating agent from dictionary: {str(e)}")
            raise ValueError(f"Invalid agent data: {str(e)}")

    def update_metrics(self, interaction_success: bool, response_time: float) -> None:
        """Update agent metrics after an interaction"""
        self.metrics['total_interactions'] += 1
        if interaction_success:
            self.metrics['successful_interactions'] += 1
        else:
            self.metrics['failed_interactions'] += 1
        
        # Update average response time
        current_avg = self.metrics['average_response_time']
        total_interactions = self.metrics['total_interactions']
        self.metrics['average_response_time'] = (
            (current_avg * (total_interactions - 1) + response_time) / total_interactions
        )
        
        self.updated_at = datetime.utcnow()

    def add_tool(self, name: str, description: Optional[str], tool_type: str) -> None:
        """Add a tool to the agent"""
        tool = Tool(name=name, description=description, type=tool_type)
        self.tools.append(tool)
        logger.info(f"Tool {name} added to agent {self.agent_id}")

    def remove_tool(self, name: str) -> None:
        """Remove a tool from the agent by name"""
        self.tools = [t for t in self.tools if t.name != name]
        self.updated_at = datetime.utcnow()
        logger.info(f"Tool {name} removed from agent {self.agent_id}")

    def update_status(self, status: str) -> None:
        """Update agent status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        logger.info(f"Agent {self.agent_id} status updated to {status}")

    def get_success_rate(self) -> float:
        """Calculate the agent's success rate"""
        total = self.metrics['total_interactions']
        if total == 0:
            return 0.0
        return self.metrics['successful_interactions'] / total * 100 