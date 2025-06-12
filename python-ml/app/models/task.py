"""Task model for team execution."""
from typing import Dict, Any, List, Optional
from datetime import datetime

class TeamTask:
    """Represents a task that can be executed by a team of agents."""
    
    def __init__(
        self,
        task_id: str,
        task_type: str,
        complexity: str,
        description: str,
        requirements: Dict[str, Any],
        priority: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        """Initialize a team task.
        
        Args:
            task_id: Unique identifier for the task
            task_type: Type of the task (e.g., 'general', 'analysis', 'coding', etc.)
            complexity: Complexity level of the task (e.g., 'low', 'medium', 'high')
            description: Description of what needs to be done
            requirements: Dictionary containing task requirements and constraints
            priority: Task priority (1-5, where 1 is lowest and 5 is highest)
            created_at: Optional creation timestamp
            updated_at: Optional last update timestamp
        """
        self.task_id = task_id
        self.task_type = task_type
        self.complexity = complexity
        self.description = description
        self.requirements = requirements
        self.priority = priority
        self.status = "pending"
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.results = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type,
            'complexity': self.complexity,
            'description': self.description,
            'requirements': self.requirements,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'results': self.results
        }
    
    def update_status(self, new_status: str) -> None:
        """Update task status and updated_at timestamp."""
        self.status = new_status
        self.updated_at = datetime.now()
    
    def add_result(self, result: Dict[str, Any]) -> None:
        """Add a result to the task's results list."""
        self.results.append(result)
        self.updated_at = datetime.now()
    
    def get_results(self) -> List[Dict[str, Any]]:
        """Get all results for this task."""
        return self.results
    
    def is_complete(self) -> bool:
        """Check if task is complete."""
        return self.status in ["completed", "failed"]
    
    def is_successful(self) -> bool:
        """Check if task completed successfully."""
        return self.status == "completed" 