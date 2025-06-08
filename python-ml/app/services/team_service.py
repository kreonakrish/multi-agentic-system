from typing import Dict, Any, List
from app.models.team import Team, TeamMember
from app.utils.enums import TaskPriority
import logging

# Get workflow-specific loggers
workflow_logger = logging.getLogger('multi_agent_system.workflow')
workflow_steps_logger = logging.getLogger('multi_agent_system.workflow.steps')
workflow_execution_logger = logging.getLogger('multi_agent_system.workflow.execution')

class TeamService:
    """Service for managing team operations"""
    
    def __init__(self):
        self.teams: Dict[str, Team] = {}

    def create_team(self, team_id: str, name: str, description: str) -> Dict[str, Any]:
        """Create a new team"""
        try:
            team = Team(team_id=team_id, name=name, description=description)
            self.teams[team_id] = team
            workflow_logger.info(f"[WORKFLOW] Team {team_id} created successfully")
            return team.to_dict()
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Failed to create team {team_id}: {str(e)}")
            raise

    def add_member(self, team_id: str, agent_id: int, 
                  priority: TaskPriority = TaskPriority.MEDIUM) -> Dict[str, Any]:
        """Add a member to a team"""
        try:
            team = self.teams.get(team_id)
            if not team:
                workflow_logger.error(f"[WORKFLOW] Team {team_id} not found")
                raise ValueError(f"Team {team_id} not found")
            
            member = TeamMember(agent_id=agent_id, priority=priority)
            team.add_member(member)
            workflow_steps_logger.info(f"[WORKFLOW_STEPS] Added member {agent_id} to team {team_id}")
            return team.to_dict()
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Failed to add member {agent_id} to team {team_id}: {str(e)}")
            raise

    def get_team(self, team_id: str) -> Dict[str, Any]:
        """Get team details"""
        try:
            team = self.teams.get(team_id)
            if not team:
                workflow_logger.error(f"[WORKFLOW] Team {team_id} not found")
                raise ValueError(f"Team {team_id} not found")
            workflow_logger.info(f"[WORKFLOW] Retrieved team {team_id}")
            return team.to_dict()
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Failed to get team {team_id}: {str(e)}")
            raise

    def get_active_teams(self) -> List[Dict[str, Any]]:
        """Get all active teams"""
        try:
            return [
                team.to_dict() for team in self.teams.values()
                if team.get_active_members()
            ]
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Failed to get active teams: {str(e)}")
            raise 