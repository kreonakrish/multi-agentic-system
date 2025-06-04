from flask import Blueprint, request, jsonify
from app.utils.logger import logger
from app.utils.decorators import log_execution
from app.utils.db import get_db_connection, safe_close_connection, db_config
from typing import Dict, Any
from datetime import datetime
import traceback

bp = Blueprint('debug', __name__, url_prefix='/api/debug')

@bp.route('/db-contents', methods=['GET'])
@log_execution
def get_db_contents() -> Dict[str, Any]:
    """Debug endpoint to check database contents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        tables = ['agents', 'agent_memory', 'messages', 'tools', 'agent_tools']
        contents = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                contents[table] = cursor.fetchall()
                # Convert datetime objects to strings for JSON serialization
                if contents[table]:
                    for row in contents[table]:
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()
                logger.info(f"Found {len(contents[table])} rows in {table}")
            except Exception as e:
                logger.error(f"Error fetching from {table}: {str(e)}")
                contents[table] = {"error": str(e)}
        
        return jsonify({
            "status": "success",
            "database_contents": contents
        })
        
    except Exception as e:
        logger.error(f"Error checking database contents: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@bp.route('/db-connection', methods=['GET'])
@log_execution
def check_db_connection() -> Dict[str, Any]:
    """Debug endpoint to verify database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try a simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Get database version
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        # Get table counts
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_ROWS
            FROM information_schema.tables
            WHERE TABLE_SCHEMA = %s
        """, (db_config['database'],))
        table_counts = cursor.fetchall()
        
        return jsonify({
            "status": "success",
            "connection": "active",
            "database": db_config['database'],
            "version": version[0] if version else None,
            "table_counts": dict(table_counts)
        })
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close() 