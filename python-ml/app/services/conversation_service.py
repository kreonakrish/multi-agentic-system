from typing import Dict, Any, Optional, List
from datetime import datetime
import json
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def store_conversation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Store conversation history in the database"""
    try:
        if not data:
            return {
                'status': 'error',
                'message': 'No data provided'
            }, 400

        required_fields = ['conversation_id', 'content', 'metadata']
        if not all(field in data for field in required_fields):
            return {
                'status': 'error',
                'message': f'Missing required fields. Required: {required_fields}'
            }, 400

        # Convert conversation_id to string if it's numeric
        conversation_id = str(data['conversation_id'])
        
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
                ) VALUES (%s, %s, %s, NOW()) AS new_data
                ON DUPLICATE KEY UPDATE
                    content = new_data.content,
                    metadata = new_data.metadata,
                    updated_at = NOW()
            """
            
            cursor.execute(insert_query, (
                conversation_id,
                json.dumps(data['content']),
                json.dumps(data['metadata'])
            ))
            
            conn.commit()

            logger.info(f"Stored conversation {conversation_id}")
            return {
                'status': 'success',
                'message': 'Conversation stored successfully',
                'conversation_id': conversation_id
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to store conversation: {str(e)}'
        }, 500

def get_conversation(conversation_id: str) -> Dict[str, Any]:
    """Get conversation details by ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get conversation details
            cursor.execute("""
                SELECT 
                    c.*,
                    cs.temperature,
                    cs.token_limit,
                    cs.start_prompt,
                    cs.end_prompt,
                    cs.style
                FROM conversations c
                LEFT JOIN conversation_settings cs ON c.settings_id = cs.id
                WHERE c.conversation_id = %s
            """, (conversation_id,))
            
            conversation = cursor.fetchone()
            if not conversation:
                return {
                    'status': 'error',
                    'message': f'Conversation {conversation_id} not found'
                }, 404

            # Convert datetime objects to strings
            for key, value in conversation.items():
                if isinstance(value, datetime):
                    conversation[key] = value.isoformat()

            return {
                'status': 'success',
                'conversation': conversation
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to get conversation: {str(e)}'
        }, 500

def get_conversation_messages(conversation_id: str) -> Dict[str, Any]:
    """Get messages for a specific conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get conversation messages
            cursor.execute("""
                SELECT cs.*,
                       a.name as agent_name,
                       t.tool_name
                FROM conversation_steps cs
                LEFT JOIN agents a ON cs.agent_id = a.id
                LEFT JOIN tools t ON cs.tool_id = t.id
                WHERE cs.conversation_id = %s
                ORDER BY cs.created_at ASC
            """, (conversation_id,))
            
            messages = cursor.fetchall()

            # Convert datetime objects to strings
            for message in messages:
                for key, value in message.items():
                    if isinstance(value, datetime):
                        message[key] = value.isoformat()

            return {
                'status': 'success',
                'messages': messages
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to get conversation messages: {str(e)}'
        }, 500

def get_conversation_settings(conversation_id: str) -> Dict[str, Any]:
    """Get settings for a specific conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get conversation settings
            cursor.execute("""
                SELECT cs.*
                FROM conversations c
                JOIN conversation_settings cs ON c.settings_id = cs.id
                WHERE c.conversation_id = %s
            """, (conversation_id,))
            
            settings = cursor.fetchone()
            if not settings:
                return {
                    'status': 'error',
                    'message': f'Settings not found for conversation {conversation_id}'
                }, 404

            # Convert datetime objects to strings
            for key, value in settings.items():
                if isinstance(value, datetime):
                    settings[key] = value.isoformat()

            return {
                'status': 'success',
                'settings': settings
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error getting conversation settings: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to get conversation settings: {str(e)}'
        }, 500

def update_conversation_settings(conversation_id: str, settings_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update settings for a specific conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # First check if conversation exists
            cursor.execute("""
                SELECT settings_id
                FROM conversations
                WHERE conversation_id = %s
            """, (conversation_id,))
            
            conversation = cursor.fetchone()
            if not conversation:
                return {
                    'status': 'error',
                    'message': f'Conversation {conversation_id} not found'
                }, 404

            if conversation['settings_id']:
                # Update existing settings
                update_query = """
                    UPDATE conversation_settings
                    SET temperature = %s,
                        token_limit = %s,
                        start_prompt = %s,
                        end_prompt = %s,
                        style = %s
                    WHERE id = %s
                """
                cursor.execute(update_query, (
                    settings_data.get('temperature'),
                    settings_data.get('token_limit'),
                    settings_data.get('start_prompt'),
                    settings_data.get('end_prompt'),
                    settings_data.get('style'),
                    conversation['settings_id']
                ))
            else:
                # Create new settings
                insert_query = """
                    INSERT INTO conversation_settings (
                        temperature,
                        token_limit,
                        start_prompt,
                        end_prompt,
                        style
                    ) VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (
                    settings_data.get('temperature'),
                    settings_data.get('token_limit'),
                    settings_data.get('start_prompt'),
                    settings_data.get('end_prompt'),
                    settings_data.get('style')
                ))
                settings_id = cursor.lastrowid

                # Update conversation with new settings_id
                cursor.execute("""
                    UPDATE conversations
                    SET settings_id = %s
                    WHERE conversation_id = %s
                """, (settings_id, conversation_id))

            conn.commit()

            return {
                'status': 'success',
                'message': 'Conversation settings updated successfully'
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error updating conversation settings: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to update conversation settings: {str(e)}'
        }, 500

def get_agent_response(agent_id: int, conversation_id: str) -> Dict[str, Any]:
    """Get agent's response in a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get agent's responses
            cursor.execute("""
                SELECT cs.*,
                       a.name as agent_name,
                       t.tool_name
                FROM conversation_steps cs
                LEFT JOIN agents a ON cs.agent_id = a.id
                LEFT JOIN tools t ON cs.tool_id = t.id
                WHERE cs.conversation_id = %s
                AND cs.agent_id = %s
                ORDER BY cs.created_at DESC
                LIMIT 1
            """, (conversation_id, agent_id))
            
            response = cursor.fetchone()
            if not response:
                return {
                    'status': 'error',
                    'message': f'No response found for agent {agent_id} in conversation {conversation_id}'
                }, 404

            # Convert datetime objects to strings
            for key, value in response.items():
                if isinstance(value, datetime):
                    response[key] = value.isoformat()

            return {
                'status': 'success',
                'response': response
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error getting agent response: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to get agent response: {str(e)}'
        }, 500

def get_conversation_steps(conversation_id: str) -> Dict[str, Any]:
    """Get all steps in a conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get conversation steps with related information
            cursor.execute("""
                SELECT 
                    cs.*,
                    a.name as agent_name,
                    t.tool_name,
                    t.tool_type
                FROM conversation_steps cs
                LEFT JOIN agents a ON cs.agent_id = a.id
                LEFT JOIN tools t ON cs.tool_id = t.id
                WHERE cs.conversation_id = %s
                ORDER BY cs.created_at ASC
            """, (conversation_id,))
            
            steps = cursor.fetchall()

            # Convert datetime objects to strings
            for step in steps:
                for key, value in step.items():
                    if isinstance(value, datetime):
                        step[key] = value.isoformat()

            return {
                'status': 'success',
                'steps': steps,
                'total_steps': len(steps)
            }

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error getting conversation steps: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': f'Failed to get conversation steps: {str(e)}'
        }, 500 