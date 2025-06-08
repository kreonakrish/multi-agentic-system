from typing import Dict, Any
from datetime import datetime
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.db import DB_CONFIG
from app.utils.logger import logger
import os

def get_db_contents() -> Dict[str, Any]:
    """Debug endpoint to check database contents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        tables = [
            'agents', 
            'agent_memory', 
            'messages', 
            'tools', 
            'agent_tools',
            'teams',
            'team_agents',
            'team_configurations',
            'team_messages',
            'team_tool_permissions',
            'workflows',
            'workflow_steps',
            'conversations',
            'conversation_steps',
            'conversation_settings',
            'documents'
        ]
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
        
        return {
            "status": "success",
            "database_contents": contents
        }
        
    except Exception as e:
        logger.error(f"Error checking database contents: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        safe_close_connection(conn, cursor)

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
        """, (DB_CONFIG['database'],))
        table_counts = cursor.fetchall()
        
        # Get connection pool status
        cursor.execute("SHOW STATUS LIKE '%connection%'")
        connection_stats = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "status": "success",
            "connection": "active",
            "database": DB_CONFIG['database'],
            "version": version[0] if version else None,
            "table_counts": dict(table_counts),
            "connection_stats": connection_stats,
            "pool_config": {
                "pool_name": DB_CONFIG['pool_name'],
                "pool_size": DB_CONFIG['pool_size'],
                "host": DB_CONFIG['host']
            }
        }
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        safe_close_connection(conn, cursor)

def get_logs() -> Dict[str, Any]:
    """Get recent application logs"""
    try:
        log_file = os.getenv('LOG_FILE', 'app.log')
        if not os.path.exists(log_file):
            return {
                "status": "error",
                "message": f"Log file {log_file} not found"
            }
            
        # Read last 1000 lines of log file
        with open(log_file, 'r') as f:
            lines = f.readlines()[-1000:]
            
        return {
            "status": "success",
            "logs": lines
        }
        
    except Exception as e:
        logger.error(f"Error reading logs: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }

def get_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        metrics = {}
        
        # Get agent metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_agents,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_agents,
                AVG(accuracy_rate) as avg_accuracy,
                AVG(success_rate) as avg_success_rate
            FROM agents
        """)
        metrics['agent_metrics'] = cursor.fetchone()
        
        # Get team metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_teams,
                COUNT(DISTINCT team_id) as active_teams
            FROM team_agents
        """)
        metrics['team_metrics'] = cursor.fetchone()
        
        # Get workflow metrics
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                AVG(TIMESTAMPDIFF(SECOND, created_at, updated_at)) as avg_duration
            FROM workflows
            GROUP BY status
        """)
        metrics['workflow_metrics'] = cursor.fetchall()
        
        # Get conversation metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_conversations,
                COUNT(DISTINCT team_id) as teams_with_conversations,
                AVG(TIMESTAMPDIFF(SECOND, started_at, ended_at)) as avg_duration
            FROM conversations
            WHERE ended_at IS NOT NULL
        """)
        metrics['conversation_metrics'] = cursor.fetchone()
        
        return {
            "status": "success",
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }
    finally:
        safe_close_connection(conn, cursor) 