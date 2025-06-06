"""Migration to add tool_responses column to workflow_steps table"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Add tool_responses column to workflow_steps table"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tool_responses column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'workflow_steps'
            AND column_name = 'tool_responses'
        """)
        has_tool_responses_column = cursor.fetchone()[0] > 0
        
        if not has_tool_responses_column:
            # Add tool_responses column
            cursor.execute("""
                ALTER TABLE workflow_steps
                ADD COLUMN tool_responses JSON NULL
                AFTER status
            """)
            
            logger.info("Added tool_responses column to workflow_steps table")
            
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error in migration: {str(e)}")
        if conn:
            conn.rollback()
        raise
        
    finally:
        safe_close_connection(conn, cursor)

if __name__ == '__main__':
    migrate() 