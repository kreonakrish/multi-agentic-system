"""
App package initialization.
"""
from flask import Flask, jsonify
from flask_cors import CORS
from app.routes import agent_routes, team_routes, tool_routes, debug_routes, conversation_routes, document_routes
from app.config.logging_config import configure_logging
import os
from dotenv import load_dotenv

def create_app(test_config=None):
    # Configure logging first
    configure_logging()

    # Load environment variables
    load_dotenv()

    # Initialize Flask app
    app = Flask(__name__)
    CORS(app)

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Register blueprints
    app.register_blueprint(agent_routes.bp, url_prefix='/api/ml/agent')
    app.register_blueprint(team_routes.bp, url_prefix='/api/ml/team')
    app.register_blueprint(tool_routes.bp, url_prefix='/api/ml/tools')
    app.register_blueprint(debug_routes.bp, url_prefix='/api/debug')
    app.register_blueprint(conversation_routes.bp, url_prefix='/api/ml/conversation')
    app.register_blueprint(document_routes.bp, url_prefix='/api/ml/documents')

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            'status': 'error',
            'message': '404 Not Found: The requested URL was not found on the server.',
            'type': 'NotFound'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'status': 'error',
            'message': 'Internal server error occurred',
            'type': 'InternalError'
        }), 500

    return app 