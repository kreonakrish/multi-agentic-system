import mysql.connector

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'admin',
    'password': 'gUest@Sep2',
    'database': 'multi_agentic_system'
}

def run_migration():
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(**db_config)
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
                    except mysql.connector.Error as err:
                        print(f"Error executing statement: {err}")
                        print(f"Statement: {statement}")
            
        conn.commit()
        print("Migration completed successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_migration() 