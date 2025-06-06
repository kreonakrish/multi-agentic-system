"""Migration to update workflows table"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

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
            
        logger.info("Updated workflows table")
            
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