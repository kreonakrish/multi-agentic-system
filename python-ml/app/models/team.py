from typing import Dict, Any, List, Optional, NamedTuple, Union
from datetime import datetime
from app.utils.enums import TaskPriority
from app.utils.logger import logger

class TeamMember:
    """Model for a team member (agent)"""
    
    def __init__(
        self,
        agent_id: int,
        priority: Union[TaskPriority, str] = TaskPriority.MEDIUM,
        accuracy_threshold: float = 0.8,
        success_rate: float = 0.0
    ):
        self.agent_id = agent_id
        # Convert string to enum if needed
        if isinstance(priority, str):
            try:
                self.priority = TaskPriority(priority)
            except ValueError:
                self.priority = TaskPriority.MEDIUM
        else:
            self.priority = priority
        self.accuracy_threshold = accuracy_threshold
        self.success_rate = success_rate
        self.total_tasks = 0
        self.successful_tasks = 0
        self.last_active = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert team member to dictionary representation"""
        return {
            'agent_id': self.agent_id,
            'priority': self.priority.value,  # Now safe to call .value
            'accuracy_threshold': self.accuracy_threshold,
            'success_rate': self.success_rate,
            'total_tasks': self.total_tasks,
            'successful_tasks': self.successful_tasks,
            'last_active': self.last_active.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamMember':
        """Create a team member instance from dictionary data"""
        member = cls(
            agent_id=data['agent_id'],
            priority=data.get('priority', TaskPriority.MEDIUM.value),
            accuracy_threshold=data.get('accuracy_threshold', 0.8),
            success_rate=data.get('success_rate', 0.0)
        )
        member.total_tasks = data.get('total_tasks', 0)
        member.successful_tasks = data.get('successful_tasks', 0)
        member.last_active = datetime.fromisoformat(data.get('last_active', datetime.utcnow().isoformat()))
        return member

    def update_metrics(self, task_success: bool) -> None:
        """Update member metrics after task completion"""
        self.total_tasks += 1
        if task_success:
            self.successful_tasks += 1
        self.success_rate = (self.successful_tasks / self.total_tasks) if self.total_tasks > 0 else 0.0
        self.last_active = datetime.utcnow()

class TeamTask:
    """Model for a team task"""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        requirements: Dict[str, Any],
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.task_id = task_id
        self.description = description
        self.requirements = requirements
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.status = 'pending'
        self.result: Optional[Dict[str, Any]] = None
        self.error_message: Optional[str] = None
        self.processing_time: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation"""
        return {
            'task_id': self.task_id,
            'description': self.description,
            'requirements': self.requirements,
            'status': self.status,
            'result': self.result,
            'error_message': self.error_message,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TeamTask':
        """Create a task instance from dictionary data"""
        task = cls(
            task_id=data['task_id'],
            description=data['description'],
            requirements=data['requirements'],
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else None
        )
        task.status = data.get('status', 'pending')
        task.result = data.get('result')
        task.error_message = data.get('error_message')
        task.processing_time = data.get('processing_time')
        return task

class Team:
    """Model for a team of agents"""
    
    def __init__(
        self,
        team_id: str,
        name: str,
        description: str,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.team_id = team_id
        self.name = name
        self.description = description
        self.members: Dict[int, TeamMember] = {}  # agent_id -> TeamMember
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.metrics: Dict[str, Any] = {
            'total_tasks': 0,
            'successful_tasks': 0,
            'failed_tasks': 0,
            'average_completion_time': 0.0
        }
        self.current_task: Optional[TeamTask] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert team to dictionary representation"""
        return {
            'team_id': self.team_id,
            'name': self.name,
            'description': self.description,
            'members': {str(agent_id): member.to_dict() for agent_id, member in self.members.items()},
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Team':
        """Create a team instance from dictionary data"""
        team = cls(
            team_id=data['team_id'],
            name=data['name'],
            description=data['description'],
            created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
            updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else None
        )
        
        # Load members
        members_data = data.get('members', {})
        for agent_id, member_data in members_data.items():
            team.members[int(agent_id)] = TeamMember.from_dict(member_data)
        
        # Load metrics
        team.metrics = data.get('metrics', team.metrics)
        return team

    def add_member(self, member: TeamMember) -> None:
        """Add a member to the team"""
        if member.agent_id not in self.members:
            self.members[member.agent_id] = member
            self.updated_at = datetime.utcnow()
            logger.info(f"Agent {member.agent_id} added to team {self.team_id}")

    def remove_member(self, agent_id: int) -> None:
        """Remove a member from the team"""
        if agent_id in self.members:
            del self.members[agent_id]
            self.updated_at = datetime.utcnow()
            logger.info(f"Agent {agent_id} removed from team {self.team_id}")

    def get_member(self, agent_id: int) -> Optional[TeamMember]:
        """Get a team member by agent ID"""
        return self.members.get(agent_id)

    def update_metrics(self, task_success: bool, completion_time: float) -> None:
        """Update team metrics after task completion"""
        self.metrics['total_tasks'] += 1
        if task_success:
            self.metrics['successful_tasks'] += 1
        else:
            self.metrics['failed_tasks'] += 1
        
        # Update average completion time
        current_avg = self.metrics['average_completion_time']
        total_tasks = self.metrics['total_tasks']
        self.metrics['average_completion_time'] = (
            (current_avg * (total_tasks - 1) + completion_time) / total_tasks
        )
        
        self.updated_at = datetime.utcnow()

    def get_success_rate(self) -> float:
        """Calculate the team's success rate"""
        total = self.metrics['total_tasks']
        if total == 0:
            return 0.0
        return (self.metrics['successful_tasks'] / total) * 100

    def get_active_members(self) -> List[TeamMember]:
        """Get list of active team members"""
        cutoff_time = datetime.utcnow() - datetime.timedelta(hours=24)
        return [
            member for member in self.members.values()
            if member.last_active > cutoff_time
        ]

    def assign_task(self, task: TeamTask) -> None:
        """Assign a task to the team"""
        self.current_task = task
        self.updated_at = datetime.utcnow()
        logger.info(f"Task {task.task_id} assigned to team {self.team_id}") 