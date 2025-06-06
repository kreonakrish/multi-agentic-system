import os
from mysql.connector import pooling
from app.utils.logger import logger

# Database configuration with environment variable support and optimized pool settings
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'gUest@Sep2'),
    'database': os.getenv('DB_NAME', 'multi_agentic_system'),
    'pool_name': 'mypool',
    'pool_size': int(os.getenv('DB_POOL_SIZE', 10)),  # Standardized pool size
    'pool_reset_session': True,
    'connect_timeout': int(os.getenv('DB_CONNECT_TIMEOUT', 10)),
    'autocommit': True,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    # Additional settings to help prevent connection issues
    'connection_timeout': 30,
    'get_warnings': True,
    'raise_on_warnings': True,
    'consume_results': True
}

_connection_pool = None

def init_db():
    """Initialize database connection pool"""
    global _connection_pool
    try:
        if _connection_pool is None:
            _connection_pool = pooling.MySQLConnectionPool(**DB_CONFIG)
            logger.info(
                "Database connection pool initialized",
                extra={
                    'pool_name': DB_CONFIG['pool_name'],
                    'pool_size': DB_CONFIG['pool_size'],
                    'host': DB_CONFIG['host'],
                    'database': DB_CONFIG['database']
                }
            )
        return _connection_pool
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
    global _connection_pool
    try:
        if _connection_pool is None:
            _connection_pool = init_db()
        
        conn = _connection_pool.get_connection()
        logger.debug("Database connection acquired from pool")
        return conn
    except pooling.PoolError as e:
        logger.error(f"Pool error getting connection: {str(e)}")
        # Try to reinitialize the pool
        try:
            _connection_pool = init_db()
            conn = _connection_pool.get_connection()
            logger.info("Successfully got connection after pool reinitialization")
            return conn
        except Exception as reinit_error:
            logger.error(f"Failed to reinitialize pool: {str(reinit_error)}")
            raise
    except Exception as e:
        logger.error(f"Error getting database connection: {str(e)}")
        raise

def safe_close_connection(conn, cursor=None):
    """Safely close cursor and connection"""
    try:
        if cursor:
            try:
                # Consume any unread results
                while cursor.fetchone() is not None:
                    pass
            except:
                pass
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

# Initialize the connection pool on module import
_connection_pool = init_db() 