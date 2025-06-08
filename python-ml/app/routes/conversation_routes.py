from flask import Blueprint, request, jsonify
from app.services.conversation_service import (
    store_conversation,
    get_conversation,
    get_conversation_messages,
    get_conversation_settings,
    update_conversation_settings,
    get_agent_response,
    get_conversation_steps
)
from app.utils.logger import logger
from app.utils.decorators import log_execution

# Create blueprint with url_prefix
bp = Blueprint('conversation', __name__, url_prefix='/api/ml/conversation')

@bp.route('/store', methods=['POST'])
@log_execution
def store_conversation_route():
    """Store conversation history in the database"""
    try:
        data = request.get_json()
        result = store_conversation(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in store_conversation route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to store conversation: {str(e)}'
        }), 500

@bp.route('/<conversation_id>', methods=['GET'])
@log_execution
def get_conversation_route(conversation_id):
    """Get conversation details by ID"""
    try:
        result = get_conversation(conversation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_conversation route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get conversation: {str(e)}'
        }), 500

@bp.route('/<conversation_id>/messages', methods=['GET'])
@log_execution
def get_conversation_messages_route(conversation_id):
    """Get messages for a specific conversation"""
    try:
        result = get_conversation_messages(conversation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_conversation_messages route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get conversation messages: {str(e)}'
        }), 500

@bp.route('/<conversation_id>/settings', methods=['GET'])
@log_execution
def get_conversation_settings_route(conversation_id):
    """Get settings for a specific conversation"""
    try:
        result = get_conversation_settings(conversation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_conversation_settings route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get conversation settings: {str(e)}'
        }), 500

@bp.route('/<conversation_id>/settings', methods=['PUT'])
@log_execution
def update_conversation_settings_route(conversation_id):
    """Update settings for a specific conversation"""
    try:
        settings_data = request.get_json()
        result = update_conversation_settings(conversation_id, settings_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in update_conversation_settings route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to update conversation settings: {str(e)}'
        }), 500

@bp.route('/<conversation_id>/agent/<int:agent_id>', methods=['GET'])
@log_execution
def get_agent_response_route(conversation_id, agent_id):
    """Get agent's response in a conversation"""
    try:
        result = get_agent_response(agent_id, conversation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_agent_response route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get agent response: {str(e)}'
        }), 500

@bp.route('/<conversation_id>/steps', methods=['GET'])
@log_execution
def get_conversation_steps_route(conversation_id):
    """Get all steps in a conversation"""
    try:
        result = get_conversation_steps(conversation_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in get_conversation_steps route: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to get conversation steps: {str(e)}'
        }), 500 