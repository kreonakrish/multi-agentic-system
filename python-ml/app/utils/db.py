import mysql.connector
from mysql.connector import pooling
import os
from app.utils.logger import logger
from typing import Optional, Tuple
from mysql.connector.cursor import MySQLCursor
from mysql.connector.connection import MySQLConnection

# Load database configuration from environment variables
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'gUest@Sep2'),
    'database': os.getenv('DB_NAME', 'multi_agentic_system'),
    'port': int(os.getenv('DB_PORT', '3306'))
}

def get_db_connection() -> MySQLConnection:
    """
    Get a database connection from the pool.
    Raises an exception if connection cannot be established.
    """
    try:
        connection = mysql.connector.connect(**db_config)
        logger.debug("Database connection established successfully")
        return connection
    except mysql.connector.Error as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def safe_close_connection(conn: Optional[MySQLConnection] = None, cursor: Optional[MySQLCursor] = None) -> None:
    """
    Safely close database connection and cursor.
    Args:
        conn: MySQL connection object
        cursor: MySQL cursor object
    """
    try:
        if cursor:
            cursor.close()
            logger.debug("Database cursor closed successfully")
    except Exception as e:
        logger.warning(f"Error closing cursor: {str(e)}")

    try:
        if conn:
            conn.close()
            logger.debug("Database connection closed successfully")
    except Exception as e:
        logger.warning(f"Error closing connection: {str(e)}") 