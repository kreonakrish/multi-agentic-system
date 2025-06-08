from app.utils.db import get_db_connection, safe_close_connection

def run_migration():
    conn = None
    cursor = None
    try:
        # Get connection from pool
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read and execute migration file
        with open('migrations/002_fix_messages_table.sql', 'r') as f:
            # Split the SQL file into individual statements
            sql_statements = f.read().split(';')
            
            # Execute each statement
            for statement in sql_statements:
                if statement.strip():
                    try:
                        cursor.execute(statement + ';')
                        print(f"Executed: {statement[:50]}...")
                    except Exception as err:
                        print(f"Error executing statement: {err}")
                        print(f"Statement: {statement}")
            
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as err:
        print(f"Error: {err}")
    finally:
        safe_close_connection(conn, cursor)

if __name__ == '__main__':
    run_migration() 