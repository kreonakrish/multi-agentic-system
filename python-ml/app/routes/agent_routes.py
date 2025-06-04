from flask import Blueprint, request, jsonify
from app.services.agent_service import AgentService
from app.utils.logger import logger
from app.utils.decorators import log_execution
from app.utils.db import get_db_connection, safe_close_connection
from datetime import datetime
from typing import Dict, Any

bp = Blueprint('agent', __name__, url_prefix='/api/ml')
agent_service = AgentService()

@bp.route('/<int:agent_id>/initialize', methods=['POST'])
@log_execution
def initialize_agent(agent_id: int) -> Dict[str, Any]:
    """Initialize an agent with the given ID"""
    try:
        result = agent_service.initialize_agent(agent_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error initializing agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to initialize agent: {str(e)}'
        }), 500

@bp.route('/<int:agent_id>/send', methods=['POST'])
@log_execution
def send_message(agent_id: int) -> Dict[str, Any]:
    """Send a message from an agent"""
    try:
        data = request.get_json()
        result = agent_service.send_message(
            agent_id,
            data.get('target_agent_id'),
            data.get('message'),
            data.get('interaction_type', 'direct')
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error sending message from agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to send message: {str(e)}'
        }), 500

@bp.route('/<int:agent_id>/receive/<int:interaction_id>', methods=['POST'])
@log_execution
def receive_message(agent_id: int, interaction_id: int) -> Dict[str, Any]:
    """Receive a message for an agent"""
    try:
        result = agent_service.receive_message(agent_id, interaction_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error receiving message for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to receive message: {str(e)}'
        }), 500

@bp.route('/<int:agent_id>/execute_all', methods=['POST'])
@log_execution
def execute_all_tools(agent_id: int) -> Dict[str, Any]:
    """Execute all tools for an agent"""
    try:
        data = request.get_json()
        result = agent_service.execute_all_tools(agent_id, data.get('command'))
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing tools for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to execute tools: {str(e)}'
        }), 500

@bp.route('/agent-interactions', methods=['GET'])
@log_execution
def get_agent_interactions() -> Dict[str, Any]:
    """Get agent interactions from messages table"""
    try:
        team_id = request.args.get('team_id')
        source = request.args.get('source')
        target = request.args.get('target')
        conversation_id = request.args.get('conversation_id')
        
        logger.info(f"[get_agent_interactions] Request params: team_id={team_id}, source={source}, target={target}, conversation_id={conversation_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query joining with agents table to get names
        query = """
            SELECT DISTINCT
                m.id,
                m.conversation_id,
                COALESCE(sa.name, 'OpenAI') as source_agent,
                COALESCE(ra.name, 'OpenAI') as target_agent,
                m.interaction_type,
                m.status,
                m.created_at as timestamp,
                m.content,
                m.processed_message,
                m.model_response
            FROM messages m
            LEFT JOIN agents sa ON m.sender_id = sa.id
            LEFT JOIN agents ra ON m.receiver_id = ra.id
            WHERE 1=1
        """
        params = []
        
        # Add filters
        if team_id:
            query += " AND m.team_id = %s"
            params.append(int(team_id))
        
        if source:
            query += " AND m.sender_id = %s"
            params.append(int(source))
            
        if target:
            query += " AND m.receiver_id = %s"
            params.append(int(target))
            
        if conversation_id:
            query += " AND m.conversation_id = %s"
            params.append(conversation_id)
            
        query += " ORDER BY m.created_at DESC"
        
        logger.info(f"[get_agent_interactions] Executing query: {query}")
        logger.info(f"[get_agent_interactions] Query params: {params}")
        
        cursor.execute(query, params)
        interactions = cursor.fetchall()
        logger.info(f"[get_agent_interactions] Found {len(interactions)} interactions")
        
        # Convert datetime objects to strings and ensure all fields are JSON serializable
        formatted_interactions = []
        for interaction in interactions:
            formatted_interaction = {}
            for key, value in interaction.items():
                if isinstance(value, datetime):
                    formatted_interaction[key] = value.isoformat()
                else:
                    formatted_interaction[key] = value
            formatted_interactions.append(formatted_interaction)
        
        logger.info(f"[get_agent_interactions] Returning {len(formatted_interactions)} formatted interactions")
        return jsonify(formatted_interactions)
        
    except Exception as e:
        logger.error(f"Error fetching agent interactions: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close() 