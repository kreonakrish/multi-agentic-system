import mysql.connector
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'gUest@Sep2')
}

def init_database():
    try:
        # Connect to MySQL server
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # Read and execute schema.sql
        with open('schema.sql', 'r') as f:
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
        print("Database initialized successfully!")
        
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    init_database() 