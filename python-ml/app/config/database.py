import os
from mysql.connector import pooling
from app.utils.logger import logger

# Database configuration with environment variable support
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'gUest@Sep2'),
    'database': os.getenv('DB_NAME', 'multi_agentic_system'),
    'pool_name': 'mypool',
    'pool_size': int(os.getenv('DB_POOL_SIZE', 20)),
    'pool_reset_session': True,
    'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', 10))
}

def init_db():
    """Initialize database connection pool"""
    try:
        connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
        logger.info(
            "Database connection pool initialized",
            extra={
                'pool_name': DB_CONFIG['pool_name'],
                'pool_size': DB_CONFIG['pool_size'],
                'host': DB_CONFIG['host'],
                'database': DB_CONFIG['database']
            }
        )
        return connection_pool
    except Exception as e:
        logger.error(
            "Failed to initialize database pool",
            extra={
                'error': str(e),
                'host': DB_CONFIG['host'],
                'database': DB_CONFIG['database']
            }
        )
        raise

def get_db_connection():
    """Get a connection from the pool with proper error handling"""
    try:
        conn = connection_pool.get_connection()
        conn.set_charset_collation('utf8mb4', 'utf8mb4_unicode_ci')
        conn.autocommit = True
        logger.debug("Database connection acquired from pool")
        return conn
    except Exception as e:
        logger.error(f"Error getting database connection: {str(e)}")
        raise

def safe_close_connection(conn, cursor=None):
    """Safely close cursor and connection"""
    try:
        if cursor:
            cursor.close()
            logger.debug("Database cursor closed")
        
        if conn:
            if not conn.in_transaction:
                conn.close()
                logger.debug("Database connection returned to pool")
            else:
                logger.warning("Rolling back uncommitted transaction")
                conn.rollback()
                conn.close()
    except Exception as e:
        logger.error(f"Error closing database connection: {str(e)}")
        if conn:
            try:
                conn._force_close()
                logger.info("Connection force closed")
            except Exception as force_close_error:
                logger.error(f"Error force closing connection: {str(force_close_error)}")

# Initialize the connection pool
connection_pool = init_db() 