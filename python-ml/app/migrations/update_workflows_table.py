"""Migration to update workflows table"""
from app.utils.db import get_db_connection, safe_close_connection
import logging

# Get workflow-specific loggers
workflow_logger = logging.getLogger('multi_agent_system.workflow')
workflow_steps_logger = logging.getLogger('multi_agent_system.workflow.steps')
workflow_execution_logger = logging.getLogger('multi_agent_system.workflow.execution')

def migrate():
    """Update workflows table with new columns"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add new columns to workflows table
        cursor.execute("""
            ALTER TABLE workflows
            ADD COLUMN team_id INT NULL,
            ADD COLUMN correlation_id VARCHAR(255) NULL,
            ADD COLUMN task_data JSON NULL,
            ADD FOREIGN KEY (team_id) REFERENCES teams(id)
        """)
            
        workflow_logger.info("[WORKFLOW] Updated workflows table with new columns")
            
        conn.commit()
        workflow_logger.info("[WORKFLOW] Migration completed successfully")
        
    except Exception as e:
        workflow_logger.error(f"[WORKFLOW] Error in migration: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        raise
        
    finally:
        safe_close_connection(conn, cursor)

if __name__ == '__main__':
    migrate() 