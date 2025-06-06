"""Migration to create agents table"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Create agents table if it doesn't exist"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create agents table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT NULL,
                accuracy_rate DECIMAL(5,2) DEFAULT 0.0,
                success_rate DECIMAL(5,2) DEFAULT 0.0,
                priority INT DEFAULT 3,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
            
        logger.info("Created agents table")
            
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