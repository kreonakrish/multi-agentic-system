"""Migration to add description column to agents table"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Add description column to agents table"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if description column exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
            AND table_name = 'agents'
            AND column_name = 'description'
        """)
        has_description_column = cursor.fetchone()[0] > 0
        
        if not has_description_column:
            # Add description column
            cursor.execute("""
                ALTER TABLE agents
                ADD COLUMN description TEXT NULL
                AFTER name
            """)
            
            logger.info("Added description column to agents table")
            
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