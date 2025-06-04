from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger

def run_migration():
    """Update agent foundation_model values to use valid OpenAI model names"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update existing agents to use gpt-3.5-turbo
        cursor.execute("""
            UPDATE agents 
            SET foundation_model = 'gpt-3.5-turbo'
            WHERE foundation_model IN ('OpenAI', 'GPT', 'Claude', 'Gemini')
        """)
        
        conn.commit()
        logger.info("Successfully updated agent foundation models")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating agent foundation models: {str(e)}")
        raise
    finally:
        safe_close_connection(conn, cursor)

if __name__ == "__main__":
    run_migration() 