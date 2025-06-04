from flask import Flask
from app.config.database import init_db
from app.config.openai_config import init_openai
from app.utils.logger import logger

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
    
    # Initialize OpenAI
    try:
        init_openai()
        logger.info("OpenAI client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        raise  # We raise this error as OpenAI is critical for our application
    
    # Register blueprints
    from app.routes import agent_routes, team_routes, tool_routes, conversation_routes, debug_routes
    
    app.register_blueprint(agent_routes.bp)
    app.register_blueprint(team_routes.bp)
    app.register_blueprint(tool_routes.bp)
    app.register_blueprint(conversation_routes.bp)
    app.register_blueprint(debug_routes.bp)
    
    logger.info("Application initialized successfully")
    return app 