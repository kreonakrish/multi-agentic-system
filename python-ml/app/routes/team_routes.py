from flask import Blueprint, request, jsonify
from app.services import team_service
from app.utils.decorators import log_execution
from app.utils.logger import logger
from app.utils.enums import TaskPriority
from typing import Dict, Any
from datetime import datetime
import uuid
import json
import traceback
from app.models.team import Team, TeamMember, TeamTask
from app.utils.db import get_db_connection, safe_close_connection
from app.services.agent_service import initialize_agent_from_db
from app.utils.task_executor import execute_task_with_team
from app.utils.workflow_manager import WorkflowManager
from app.utils.logger import (
    workflow_logger,
    workflow_steps_logger,
    workflow_execution_logger,
    workflow_decision_logger
)
from app.utils.team_utils import aggregate_team_responses


# Create blueprint without url_prefix (will be set in app.py)
bp = Blueprint('team', __name__)

def _convert_priority(priority_value: Any) -> TaskPriority:
    """Convert a priority value to TaskPriority enum"""
    if isinstance(priority_value, TaskPriority):
        return priority_value
    
    # If it's a string, try to convert directly
    if isinstance(priority_value, str):
        try:
            return TaskPriority(priority_value.lower())
        except ValueError:
            pass
    
    # If it's a number, map to priority levels
    if isinstance(priority_value, (int, float)):
        if priority_value <= 1:
            return TaskPriority.LOW
        elif priority_value <= 2:
            return TaskPriority.MEDIUM
        elif priority_value <= 3:
            return TaskPriority.HIGH
        else:
            return TaskPriority.CRITICAL
    
    # Default to MEDIUM priority
    return TaskPriority.MEDIUM

@bp.route('/execute', methods=['POST'])
@log_execution
def execute_team_task():
    try:
        # Get request data
        data = request.get_json()
        workflow_logger.debug(f"[WORKFLOW] Received request data: {json.dumps(data, indent=2)}")
        
        if not data:
            workflow_logger.error("[WORKFLOW] Request body is required")
            return jsonify({
                'status': 'error',
                'message': 'Request body is required'
            }), 400
        
        # Extract team_id and task_id from context
        context = data.get('context', {})
        team_id = context.get('team_id')
        team_config = context.get('team_config', {})
        
        if not team_id or not team_config:
            workflow_logger.error("[WORKFLOW] team_id and team_config are required in context")
            return jsonify({
                'status': 'error',
                'message': 'team_id and team_config are required in context'
            }), 400
        
        # Initialize team
        team = Team(team_id=team_id, name=team_config.get('name', ''), description=team_config.get('description', ''))
        
        # Create task
        task = TeamTask(
            task_id=str(uuid.uuid4()),
            task_type=data.get('task_type', 'general'),
            complexity=data.get('complexity', 'medium'),
            description=data.get('content', ''),
            requirements=context,
            priority=data.get('priority', 1)
        )
        
        workflow_logger.info(f"[WORKFLOW] Initializing team task execution")
        workflow_logger.info(f"[WORKFLOW] Team ID: {team_id}")
        workflow_logger.info(f"[WORKFLOW] Task ID: {task.task_id}")
        workflow_logger.info(f"[WORKFLOW] Task Type: {task.task_type}")
        workflow_logger.info(f"[WORKFLOW] Task Complexity: {task.complexity}")
        workflow_logger.info(f"[WORKFLOW] Task Priority: {task.priority}")
        
        # Initialize workflow manager
        workflow_manager = WorkflowManager()
        
        # Execute workflow
        final_result = workflow_manager.execute_workflow(team, task)
        workflow_logger.info("[WORKFLOW] Workflow execution completed")
        
        # Aggregate team responses
        aggregated = aggregate_team_responses(final_result.get('results', []), task.description)
        workflow_logger.info("[WORKFLOW] Team responses aggregated")
        
        # Prepare response
        response = {
            "status": "success",
            "task_id": task.task_id,
            "team_id": str(team.team_id),
            "workflow_id": final_result.get('workflow_id'),
            "results": final_result.get('results', []),
            "conversation_context": final_result.get('conversation_context', []),
            "final_status": final_result.get('final_status', 'failed'),
            "aggregated_data": aggregated.get('aggregated_data', {
                'vector_store': {
                    'results': [],
                    'queries': [],
                    'datasets': []
                },
                'raw_data': {
                    'samples': [],
                    'total_records': 0,
                    'schemas': []
                },
                'tool_results': [],
                'llm_responses': [],
                'visualizations': []
            }),
            "validation_result": aggregated.get('validation_result'),
            "execution_summary": {
                "total_agents": final_result.get('execution_summary', {}).get('total_agents', 0),
                "successful_executions": final_result.get('execution_summary', {}).get('successful_agents', 0),
                "priority_groups": final_result.get('execution_summary', {}).get('priority_groups', []),
                "execution_order": final_result.get('execution_summary', {}).get('execution_order', [])
            }
        }
        
        # Add visualization data to the response if available
        if aggregated.get('aggregated_data', {}).get('visualizations'):
            response['visualization_data'] = {
                'charts': aggregated['aggregated_data']['visualizations']
            }
        
        workflow_logger.info("[WORKFLOW] Task execution completed successfully")
        workflow_logger.debug(f"[WORKFLOW] Response: {json.dumps(response, indent=2)}")
        
        return jsonify(response)
        
    except Exception as e:
        workflow_logger.error(f"[WORKFLOW] Error in team task execution: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/create', methods=['POST'])
@log_execution
def create_team() -> Dict[str, Any]:
    """Create a new team"""
    try:
        data = request.get_json()
        result = team_service.create_team(
            team_id=data['team_id'],
            name=data['name'],
            description=data.get('description', '')
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error creating team: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to create team: {str(e)}'
        }), 500

@bp.route('/<team_id>/member', methods=['POST'])
@log_execution
def add_team_member(team_id: str) -> Dict[str, Any]:
    """Add a member to a team"""
    try:
        data = request.get_json()
        result = team_service.add_member(
            team_id=team_id,
            agent_id=data['agent_id'],
            priority=TaskPriority(data.get('priority', TaskPriority.MEDIUM.value))
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error adding team member: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to add team member: {str(e)}'
        }), 500

@bp.route('/<team_id>', methods=['GET'])
@log_execution
def get_team(team_id: str) -> Dict[str, Any]:
    """Get team details"""
    try:
        result = team_service.get_team(team_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting team: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get team: {str(e)}'
        }), 500

@bp.route('/active', methods=['GET'])
@log_execution
def get_active_teams() -> Dict[str, Any]:
    """Get all active teams"""
    try:
        result = team_service.get_active_teams()
        return jsonify({
            'status': 'success',
            'teams': result
        })
    except Exception as e:
        logger.error(f"Error getting active teams: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get active teams: {str(e)}'
        }), 500

@bp.route('/history', methods=['GET'])
@log_execution
def get_team_history():
    """Get history of team messages and tasks"""
    try:
        team_id = request.args.get('team_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        return team_service.get_team_history(team_id, start_date, end_date)
    except Exception as e:
        logger.error(f"Error fetching team history: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@bp.route('/<int:team_id>/members', methods=['GET', 'POST'])
@log_execution
def manage_team_members(team_id: int) -> Dict[str, Any]:
    """Manage team members"""
    try:
        if request.method == 'GET':
            return team_service.get_team_members(team_id)
        else:  # POST
            data = request.get_json()
            return team_service.update_team_members(team_id, data)
    except Exception as e:
        logger.error(f"Error managing team members: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to manage team members: {str(e)}'
        }), 500

@bp.route('/<int:team_id>/member/<int:agent_id>', methods=['DELETE'])
@log_execution
def remove_team_member(team_id: int, agent_id: int) -> Dict[str, Any]:
    """Remove a member from a team"""
    try:
        return team_service.remove_team_member(team_id, agent_id)
    except Exception as e:
        logger.error(f"Error removing team member: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to remove team member: {str(e)}'
        }), 500

@bp.route('/<int:team_id>/config', methods=['GET', 'PUT'])
@log_execution
def manage_team_config(team_id: int) -> Dict[str, Any]:
    """Manage team configuration"""
    try:
        if request.method == 'GET':
            return team_service.get_team_config(team_id)
        else:  # PUT
            data = request.get_json()
            return team_service.update_team_config(team_id, data)
    except Exception as e:
        logger.error(f"Error managing team config: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to manage team config: {str(e)}'
        }), 500 