from flask import Blueprint, request, jsonify
from app.services.tool_service import ToolService
from app.utils.logger import logger
from app.utils.decorators import log_execution
from typing import Dict, Any

bp = Blueprint('tool', __name__, url_prefix='/api/ml/tool')
tool_service = ToolService()

@bp.route('/create', methods=['POST'])
@log_execution
def create_tool() -> Dict[str, Any]:
    """Create a new tool"""
    try:
        data = request.get_json()
        result = tool_service.create_tool(data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error creating tool: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to create tool: {str(e)}'
        }), 500

@bp.route('/<int:tool_id>', methods=['GET'])
@log_execution
def get_tool(tool_id: int) -> Dict[str, Any]:
    """Get tool details"""
    try:
        tool = tool_service.get_tool(tool_id)
        return jsonify(tool_service.get_tool_info(tool))
    except Exception as e:
        logger.error(f"Error getting tool: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to get tool: {str(e)}'
        }), 500

@bp.route('/<int:tool_id>/execute', methods=['POST'])
@log_execution
def execute_tool(tool_id: int) -> Dict[str, Any]:
    """Execute a command using a tool"""
    try:
        data = request.get_json()
        result = tool_service.execute_tool(tool_id, data['command'])
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error executing tool: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to execute tool: {str(e)}'
        }), 500

@bp.route('/list', methods=['GET'])
@log_execution
def list_tools() -> Dict[str, Any]:
    """List all available tools"""
    try:
        tools = tool_service.list_tools()
        return jsonify({
            'status': 'success',
            'tools': tools
        })
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to list tools: {str(e)}'
        }), 500

@bp.route('/<int:tool_id>', methods=['DELETE'])
@log_execution
def delete_tool(tool_id: int) -> Dict[str, Any]:
    """Delete a tool"""
    try:
        tool_service.delete_tool(tool_id)
        return jsonify({
            'status': 'success',
            'message': f'Tool {tool_id} deleted successfully'
        })
    except Exception as e:
        logger.error(f"Error deleting tool: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to delete tool: {str(e)}'
        }), 500 