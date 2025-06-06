"""Migration to add agent metrics columns"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Add accuracy_rate, success_rate, and priority columns to agents table"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'agents'
            AND column_name IN ('accuracy_rate', 'success_rate', 'priority')
        """)
        columns_exist = cursor.fetchone()[0] == 3
        
        if not columns_exist:
            # Add columns
            cursor.execute("""
                ALTER TABLE agents
                ADD COLUMN accuracy_rate DECIMAL(5,2) DEFAULT 0.0,
                ADD COLUMN success_rate DECIMAL(5,2) DEFAULT 0.0,
                ADD COLUMN priority INT DEFAULT 3
            """)
            
            logger.info("Added agent metrics columns to agents table")
            
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