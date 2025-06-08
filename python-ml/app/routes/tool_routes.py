from flask import Blueprint, request, jsonify
from app.services import tool_service
from app.utils.decorators import log_execution

bp = Blueprint('tool', __name__)

@bp.route('/', methods=['GET'])
@log_execution
def get_tools():
    return tool_service.get_all_tools()

@bp.route('/<int:tool_id>', methods=['GET', 'PUT'])
@log_execution
def manage_tool(tool_id):
    if request.method == 'GET':
        return tool_service.get_tool(tool_id)
    else:
        data = request.get_json()
        return tool_service.update_tool(tool_id, data)

@bp.route('/<int:tool_id>/execute', methods=['POST'])
@log_execution
def execute_tool(tool_id):
    data = request.get_json()
    return tool_service.execute_tool(tool_id, data)

@bp.route('/<int:tool_id>/permissions', methods=['GET', 'POST'])
@log_execution
def manage_tool_permissions(tool_id):
    if request.method == 'GET':
        return tool_service.get_tool_permissions(tool_id)
    else:
        data = request.get_json()
        return tool_service.add_tool_permission(tool_id, data) 