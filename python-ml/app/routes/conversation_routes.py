from flask import Blueprint, request, jsonify
from app.utils.logger import logger
from app.utils.decorators import log_execution
from app.utils.db import get_db_connection, safe_close_connection
from typing import Dict, Any
import json

bp = Blueprint('conversation', __name__, url_prefix='/api/ml/conversation')

@bp.route('/store', methods=['POST'])
@log_execution
def store_conversation() -> Dict[str, Any]:
    """Store conversation history in the database"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['conversation_id', 'content', 'metadata']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Missing required fields. Required: {required_fields}'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Store the conversation
            insert_query = """
                INSERT INTO conversations (
                    conversation_id,
                    content,
                    metadata,
                    created_at
                ) VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    content = VALUES(content),
                    metadata = VALUES(metadata),
                    updated_at = NOW()
            """
            
            cursor.execute(insert_query, (
                data['conversation_id'],
                json.dumps(data['content']),
                json.dumps(data['metadata'])
            ))
            
            conn.commit()

            logger.info(f"Stored conversation {data['conversation_id']}")
            return jsonify({
                'status': 'success',
                'message': 'Conversation stored successfully',
                'conversation_id': data['conversation_id']
            })

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to store conversation: {str(e)}'
        }), 500 