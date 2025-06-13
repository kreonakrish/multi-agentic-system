"""Database migration runner."""
import os
from app.utils.db import get_db_connection
from app.utils.logger import workflow_logger

def run_migrations():
    """Run all database migrations."""
    try:
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all SQL files in migrations directory
        migration_dir = os.path.dirname(os.path.abspath(__file__))
        sql_files = [f for f in os.listdir(migration_dir) if f.endswith('.sql')]
        sql_files.sort()  # Ensure migrations run in order
        
        # Run each migration
        for sql_file in sql_files:
            try:
                # Read SQL file
                with open(os.path.join(migration_dir, sql_file), 'r') as f:
                    sql = f.read()
                
                # Execute SQL
                cursor.execute(sql)
                conn.commit()
                
                workflow_logger.info(f"Successfully ran migration: {sql_file}")
                
            except Exception as e:
                workflow_logger.error(f"Error running migration {sql_file}: {str(e)}", exc_info=True)
                conn.rollback()
                raise
        
        workflow_logger.info("All migrations completed successfully")
        
    except Exception as e:
        workflow_logger.error(f"Error running migrations: {str(e)}", exc_info=True)
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    run_migrations() 