from enum import Enum

class InteractionType(Enum):
    """Types of interactions between agents"""
    DIRECT = "direct"
    WORKFLOW = "workflow"
    BROADCAST = "broadcast"
    CHAIN = "chain"

class InteractionStatus(Enum):
    """Status of agent interactions"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ToolPermissionLevel(Enum):
    """Permission levels for tool access"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"

class AgentStatus(Enum):
    """Status of an agent"""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

class TaskPriority(Enum):
    """Priority levels for tasks"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical" 