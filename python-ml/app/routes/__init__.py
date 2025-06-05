from flask import Blueprint

# Create blueprints
agent_bp = Blueprint('agent', __name__, url_prefix='/api/ml/agent')
tool_bp = Blueprint('tool', __name__, url_prefix='/api/ml/tool')
team_bp = Blueprint('team', __name__, url_prefix='/api/ml/team')

# Import routes
from . import agent_routes
from . import tool_routes
from . import team_routes 