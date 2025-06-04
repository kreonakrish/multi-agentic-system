from flask import Blueprint, request, jsonify
from app.services.team_service import TeamService
from app.utils.logger import logger
from app.utils.decorators import log_execution
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

bp = Blueprint('team', __name__, url_prefix='/api/ml/team')
team_service = TeamService()

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
    """Execute a task using a team of agents"""
    conn = None
    cursor = None
    start_time = datetime.now()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        # Validate required fields
        required_fields = ['team_config', 'task']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        # Get team_id from config, fallback to UUID if not provided
        team_id = str(data['team_config'].get('team_id', uuid.uuid4()))
        
        # Create team instance with the provided team_id
        team = Team(
            team_id=team_id,
            name=data['team_config'].get('name', 'Task Team'),
            description=data['team_config'].get('description', 'Team for task execution')
        )

        # Add team members
        for member_config in data['team_config'].get('members', []):
            # Convert priority value to TaskPriority enum
            priority = _convert_priority(member_config.get('priority'))
            
            member = TeamMember(
                agent_id=member_config['agent_id'],
                priority=priority,
                accuracy_threshold=member_config.get('accuracy_threshold', 0.8),
                success_rate=member_config.get('success_rate', 0.9)
            )
            team.add_member(member)

        if not team.members:
            return jsonify({
                "status": "error",
                "message": "No team members specified"
            }), 400

        # Create task
        task = TeamTask(
            task_id=str(uuid.uuid4()),
            description=data['task'].get('description', ''),
            requirements=data['task'].get('requirements', {})
        )
        team.assign_task(task)

        # Store initial task record
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            insert_query = """
                INSERT INTO team_messages (
                    team_id, task_id, task_description, task_requirements, 
                    team_config, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                team.team_id,
                task.task_id,
                task.description,
                json.dumps(task.requirements),
                json.dumps(data['team_config']),
                'processing'
            ))
            
            conn.commit()
            logger.info(f"Stored initial team task record for task {task.task_id}")
            
        except Exception as db_error:
            logger.error(f"Database error storing team task: {str(db_error)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            safe_close_connection(conn, cursor)

        # Execute task with team
        final_result = execute_task_with_team(team, task)
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds())

        # Update task record with results
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            update_query = """
                UPDATE team_messages 
                SET status = %s,
                    result = %s,
                    processing_time = %s,
                    agent_responses = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE team_id = %s AND task_id = %s
            """
            
            cursor.execute(update_query, (
                final_result.get('final_status', 'failed'),
                json.dumps(final_result),
                processing_time,
                json.dumps(final_result.get('conversation_context', [])),
                team.team_id,
                task.task_id
            ))
            
            conn.commit()
            logger.info(f"Updated team task record with results for task {task.task_id}")
            
        except Exception as db_error:
            logger.error(f"Database error updating team task results: {str(db_error)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            safe_close_connection(conn, cursor)

        return jsonify({
            "status": "success",
            "team": team.to_dict(),
            "result": final_result,
            "processing_time_seconds": processing_time
        })

    except Exception as e:
        logger.error(f"Error executing team task: {str(e)}", exc_info=True)
        
        # Store error in database if we have team/task IDs
        if 'team' in locals() and 'task' in locals():
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                update_query = """
                    UPDATE team_messages 
                    SET status = 'failed',
                        error_message = %s,
                        processing_time = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE team_id = %s AND task_id = %s
                """
                
                processing_time = int((datetime.now() - start_time).total_seconds())
                
                cursor.execute(update_query, (
                    str(e),
                    processing_time,
                    team.team_id,
                    task.task_id
                ))
                
                conn.commit()
                
            except Exception as db_error:
                logger.error(f"Database error storing team task error: {str(db_error)}", exc_info=True)
            finally:
                safe_close_connection(conn, cursor)
        
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc()
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
def get_team_history():
    """Get history of team messages and tasks"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get optional query parameters
        team_id = request.args.get('team_id')
        status = request.args.get('status')
        limit = request.args.get('limit', 100)
        
        # Build query
        query = "SELECT * FROM team_messages WHERE 1=1"
        params = []
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
            
        if status:
            query += " AND status = %s"
            params.append(status)
            
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(int(limit))
        
        # Execute query
        cursor.execute(query, tuple(params))
        history = cursor.fetchall()
        
        # Convert datetime objects to strings
        for record in history:
            record['created_at'] = record['created_at'].isoformat() if record['created_at'] else None
            record['updated_at'] = record['updated_at'].isoformat() if record['updated_at'] else None
        
        return jsonify({
            "status": "success",
            "history": history
        })
        
    except Exception as e:
        logger.error(f"Error fetching team history: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        safe_close_connection(conn, cursor) 