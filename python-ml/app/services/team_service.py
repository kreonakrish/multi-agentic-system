from typing import Dict, Any, List
from app.models.team import Team, TeamMember
from app.utils.enums import TaskPriority
from app.utils.team_utils import get_team_agents_ordered
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import (
    workflow_logger,
    workflow_steps_logger,
    workflow_execution_logger,
    workflow_decision_logger
)

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

    def get_team_members(self, team_id: int) -> Dict[str, Any]:
        """Get team members ordered by priority"""
        try:
            # First try to get from in-memory cache
            team = self.teams.get(str(team_id))
            if team:
                return {
                    'status': 'success',
                    'members': [member.to_dict() for member in team.members]
                }
            
            # If not in cache, get from database
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=False)  # Use tuple-based cursor for better performance
            try:
                members = get_team_agents_ordered(cursor, team_id)
                if not members:
                    workflow_logger.warning(f"[WORKFLOW] No members found for team {team_id}")
                    return {
                        'status': 'error',
                        'message': f'No members found for team {team_id}'
                    }
                
                workflow_logger.info(f"[WORKFLOW] Found {len(members)} members for team {team_id}")
                return {
                    'status': 'success',
                    'members': members
                }
            finally:
                safe_close_connection(conn, cursor)
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Failed to get team members for team {team_id}: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to get team members: {str(e)}'
            }

# Create a singleton instance
_team_service = TeamService()

# Export module-level functions that delegate to the singleton
def create_team(team_id: str, name: str, description: str) -> Dict[str, Any]:
    return _team_service.create_team(team_id, name, description)

def add_member(team_id: str, agent_id: int, priority: TaskPriority = TaskPriority.MEDIUM) -> Dict[str, Any]:
    return _team_service.add_member(team_id, agent_id, priority)

def get_team(team_id: str) -> Dict[str, Any]:
    return _team_service.get_team(team_id)

def get_active_teams() -> List[Dict[str, Any]]:
    return _team_service.get_active_teams()

def get_team_members(team_id: int) -> Dict[str, Any]:
    return _team_service.get_team_members(team_id)

def update_team_members(team_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    return _team_service.update_team_members(team_id, data)

def remove_team_member(team_id: int, agent_id: int) -> Dict[str, Any]:
    return _team_service.remove_team_member(team_id, agent_id)

def get_team_config(team_id: int) -> Dict[str, Any]:
    return _team_service.get_team_config(team_id)

def update_team_config(team_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
    return _team_service.update_team_config(team_id, data) 