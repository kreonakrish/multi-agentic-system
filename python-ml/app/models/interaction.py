from enum import Enum
from typing import Dict, Any

class InteractionType(Enum):
    DIRECT = "direct"
    WORKFLOW = "workflow"
    BROADCAST = "broadcast"
    CHAIN = "chain"

class InteractionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentInteraction:
    def __init__(self, 
                 interaction_id: int,
                 source_agent_id: int,
                 target_agent_id: int,
                 interaction_type: str,
                 message: str,
                 status: str = InteractionStatus.PENDING.value):
        self.interaction_id = interaction_id
        self.source_agent_id = source_agent_id
        self.target_agent_id = target_agent_id
        self.interaction_type = interaction_type
        self.message = message
        self.status = status

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "interaction_type": self.interaction_type,
            "message": self.message,
            "status": self.status
        } 