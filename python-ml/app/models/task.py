"""Task model for team execution."""
from typing import Dict, Any, List
from datetime import datetime

class TeamTask:
    """Represents a task that can be executed by a team of agents."""
    
    def __init__(self, task_id: str, description: str, requirements: Dict[str, Any]):
        """Initialize a team task.
        
        Args:
            task_id: Unique identifier for the task
            description: Description of what needs to be done
            requirements: Dictionary containing task requirements and constraints
        """
        self.task_id = task_id
        self.description = description
        self.requirements = requirements
        self.status = "pending"
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.results = []
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            'task_id': self.task_id,
            'description': self.description,
            'requirements': self.requirements,
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