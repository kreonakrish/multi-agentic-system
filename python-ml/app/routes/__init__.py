from flask import Blueprint

# Create blueprints
agent_bp = Blueprint('agent', __name__, url_prefix='/api/ml/agent')
tool_bp = Blueprint('tool', __name__, url_prefix='/api/ml/tool')
team_bp = Blueprint('team', __name__, url_prefix='/api/ml/team')
document_bp = Blueprint('document', __name__, url_prefix='/api/ml/documents')
conversation_bp = Blueprint('conversation', __name__, url_prefix='/api/ml/conversation')
debug_bp = Blueprint('debug', __name__, url_prefix='/api/debug')

# Import routes
from . import agent_routes
from . import tool_routes
from . import team_routes
from . import document_routes
from . import conversation_routes
from . import debug_routes 