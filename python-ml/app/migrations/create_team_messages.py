"""Migration to create team_messages table"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Create team_messages table if it doesn't exist"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create team_messages table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                team_id INT NOT NULL,
                message_type ENUM('task', 'response', 'notification') NOT NULL,
                message_data JSON NOT NULL,
                correlation_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)
            
        logger.info("Created team_messages table")
            
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