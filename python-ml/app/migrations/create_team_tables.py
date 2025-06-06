"""Migration to create teams and team_agents tables"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Create teams and team_agents tables if they don't exist"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create teams table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # Create team_agents table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                team_id INT NOT NULL,
                agent_id INT NOT NULL,
                priority INT DEFAULT 3,
                accuracy_rate DECIMAL(5,2) DEFAULT 0.0,
                success_rate DECIMAL(5,2) DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
            
        logger.info("Created teams and team_agents tables")
            
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