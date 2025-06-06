"""Migration to create workflows and workflow_steps tables"""
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def migrate():
    """Create workflows and workflow_steps tables if they don't exist"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create workflows table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id INT AUTO_INCREMENT PRIMARY KEY,
                correlation_id VARCHAR(255) NOT NULL,
                team_id INT NOT NULL,
                status ENUM('pending', 'in_progress', 'completed', 'failed') DEFAULT 'pending',
                task_data JSON NOT NULL,
                response_data JSON NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id)
            )
        """)
        
        # Create workflow_steps table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflow_steps (
                id INT AUTO_INCREMENT PRIMARY KEY,
                workflow_id INT NOT NULL,
                agent_id INT NOT NULL,
                status ENUM('pending', 'in_progress', 'completed', 'failed') DEFAULT 'pending',
                tool_responses JSON NULL,
                error_message TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES workflows(id),
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
            
        logger.info("Created workflows and workflow_steps tables")
            
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