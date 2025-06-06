from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import time
from datetime import datetime
import traceback
from app.utils.logger import logger
from app.routes import team_routes, tool_routes, agent_routes
from app.utils.db import init_db, get_db_connection, safe_close_connection

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Initialize database
    init_db()
    
    # Register blueprints
    app.register_blueprint(team_routes.bp, url_prefix='/api/teams')
    app.register_blueprint(tool_routes.bp, url_prefix='/api/tools')
    app.register_blueprint(agent_routes.bp, url_prefix='/api/agents')
    
    @app.before_request
    def log_request():
        """Log incoming request details"""
        request.start_time = time.time()
        
        # Get request details
        method = request.method
        url = request.url
        headers = dict(request.headers)
        # Remove sensitive headers
        if 'Authorization' in headers:
            headers['Authorization'] = 'REDACTED'
        if 'Cookie' in headers:
            headers['Cookie'] = 'REDACTED'
            
        body = None
        if request.is_json:
            try:
                body = request.get_json()
            except Exception as e:
                body = "(invalid JSON)"
        elif request.form:
            body = dict(request.form)
        elif request.data:
            try:
                body = request.data.decode('utf-8')
            except:
                body = "(binary data)"
                
        # Log request
        logger.info(f"\n{'='*80}\n[REQUEST START] {datetime.now().isoformat()}")
        logger.info(f"[REQUEST METHOD] {method}")
        logger.info(f"[REQUEST URL] {url}")
        logger.info(f"[REQUEST HEADERS] {json.dumps(headers, indent=2)}")
        if body:
            logger.info(f"[REQUEST BODY] {json.dumps(body, indent=2) if isinstance(body, (dict, list)) else body}")
        logger.info(f"{'='*80}")
    
    @app.after_request
    def log_response(response):
        """Log outgoing response details"""
        # Calculate request duration
        duration = time.time() - request.start_time
        
        # Get response details
        status_code = response.status_code
        headers = dict(response.headers)
        
        # Try to parse and format response body
        try:
            body = response.get_json() if response.is_json else response.get_data(as_text=True)
        except:
            body = "(binary data)"
            
        # Log response
        logger.info(f"\n{'='*80}\n[RESPONSE START] {datetime.now().isoformat()}")
        logger.info(f"[RESPONSE TIME] {duration:.3f} seconds")
        logger.info(f"[RESPONSE STATUS] {status_code}")
        logger.info(f"[RESPONSE HEADERS] {json.dumps(headers, indent=2)}")
        if body:
            logger.info(f"[RESPONSE BODY] {json.dumps(body, indent=2) if isinstance(body, (dict, list)) else body}")
        logger.info(f"{'='*80}")
        
        return response
    
    @app.errorhandler(Exception)
    def handle_error(error):
        """Handle and log any unhandled exceptions"""
        logger.error(f"\n{'='*80}\n[ERROR] Unhandled exception occurred:")
        logger.error(traceback.format_exc())
        logger.error(f"{'='*80}")
        
        return jsonify({
            'status': 'error',
            'message': str(error),
            'type': error.__class__.__name__
        }), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000) 