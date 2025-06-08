from flask import Blueprint, jsonify
from app.services import debug_service
from app.utils.decorators import log_execution

bp = Blueprint('debug', __name__)

@bp.route('/api/debug/db-contents', methods=['GET'])
@log_execution
def get_db_contents():
    return debug_service.get_db_contents()

@bp.route('/api/debug/db-connection', methods=['GET'])
@log_execution
def check_db_connection():
    return debug_service.check_db_connection()

@bp.route('/api/debug/logs', methods=['GET'])
@log_execution
def get_logs():
    return debug_service.get_logs()

@bp.route('/api/debug/metrics', methods=['GET'])
@log_execution
def get_metrics():
    return debug_service.get_metrics() 