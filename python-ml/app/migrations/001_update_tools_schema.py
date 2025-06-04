from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Update tools table schema to include tool_type column"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if type column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'tools'
            AND column_name = 'tool_type'
        """)
        has_type_column = cursor.fetchone()[0] > 0
        
        if not has_type_column:
            # Add tool_type column
            cursor.execute("""
                ALTER TABLE tools
                ADD COLUMN tool_type VARCHAR(50) NOT NULL DEFAULT 'unknown'
            """)
            logger.info("Added tool_type column to tools table")
            
            # Update existing tools with appropriate types
            cursor.execute("""
                UPDATE tools
                SET tool_type = 'api'
                WHERE hostname IS NOT NULL
            """)
            
            cursor.execute("""
                UPDATE tools
                SET tool_type = 'system'
                WHERE hostname IS NULL
            """)
            logger.info("Updated existing tools with appropriate types")
        
        # Update the query in agent_service to use tool_type instead of type
        cursor.execute("""
            SELECT t.tool_name, t.description, t.tool_type
            FROM agent_tools at
            JOIN tools t ON at.tool_id = t.id
            LIMIT 1
        """)
        logger.info("Verified tools table schema update")
        
        conn.commit()
        logger.info("Tools table migration completed successfully")
        
    except Exception as e:
        logger.error(f"Error during tools table migration: {str(e)}")
        if conn:
            conn.rollback()
        raise
    finally:
        safe_close_connection(conn, cursor) 