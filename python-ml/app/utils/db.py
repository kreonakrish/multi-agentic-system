import os
import mysql.connector
from mysql.connector import pooling
import logging
from app.utils.logger import logger
import time

logger = logging.getLogger(__name__)

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
_max_retries = 3
_retry_delay = 1  # seconds

def init_db():
    """Initialize database connection pool"""
    global _connection_pool
    retry_count = 0
    
    while retry_count < _max_retries:
        try:
            if _connection_pool is not None:
                try:
                    # Test the existing pool
                    test_conn = _connection_pool.get_connection()
                    test_conn.close()
                    logger.info("Existing connection pool is valid")
                    return _connection_pool
                except Exception as e:
                    logger.warning(f"Existing pool is invalid, reinitializing: {str(e)}")
                    _connection_pool = None
            
            pool = mysql.connector.pooling.MySQLConnectionPool(**DB_CONFIG)
            logger.info(
                "Database connection pool initialized",
                extra={
                    'pool_name': DB_CONFIG['pool_name'],
                    'pool_size': DB_CONFIG['pool_size'],
                    'host': DB_CONFIG['host'],
                    'database': DB_CONFIG['database']
                }
            )
            return pool
            
        except Exception as e:
            retry_count += 1
            logger.error(
                f"Failed to initialize database pool (attempt {retry_count}/{_max_retries})",
                extra={
                    'error': str(e),
                    'host': DB_CONFIG['host'],
                    'database': DB_CONFIG['database']
                }
            )
            if retry_count < _max_retries:
                time.sleep(_retry_delay)
            else:
                raise

def get_db_connection():
    """Get a connection from the pool with proper error handling"""
    global _connection_pool
    retry_count = 0
    
    while retry_count < _max_retries:
        try:
            if _connection_pool is None:
                _connection_pool = init_db()
            
            conn = _connection_pool.get_connection()
            
            # Test the connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            
            logger.debug("Database connection acquired and validated from pool")
            return conn
            
        except mysql.connector.errors.PoolError as e:
            logger.error(f"Pool error getting connection: {str(e)}")
            _connection_pool = None  # Force pool reinitialization
            retry_count += 1
            if retry_count < _max_retries:
                time.sleep(_retry_delay)
            else:
                raise
                
        except Exception as e:
            logger.error(f"Error getting database connection: {str(e)}")
            retry_count += 1
            if retry_count < _max_retries:
                time.sleep(_retry_delay)
            else:
                raise

def safe_close_connection(conn, cursor=None):
    """Safely close cursor and connection"""
    try:
        # First handle cursor cleanup
        if cursor:
            try:
                # Consume any unread results
                while cursor.fetchone() is not None:
                    pass
            except:
                pass
            try:
                cursor.close()
                logger.debug("Database cursor closed")
            except Exception as e:
                logger.warning(f"Error closing cursor: {str(e)}")

        # Then handle connection cleanup
        if conn:
            try:
                # Check if connection is still valid
                if hasattr(conn, '_cnx') and conn._cnx is not None:
                    if hasattr(conn, 'in_transaction') and conn.in_transaction:
                        logger.warning("Rolling back uncommitted transaction")
                        try:
                            conn.rollback()
                        except Exception as e:
                            logger.warning(f"Error rolling back transaction: {str(e)}")
                    
                    try:
                        conn.close()
                        logger.debug("Database connection returned to pool")
                    except Exception as e:
                        logger.warning(f"Error closing connection normally: {str(e)}")
                        # Try force close as last resort
                        if hasattr(conn, '_force_close'):
                            try:
                                conn._force_close()
                                logger.info("Connection force closed")
                            except Exception as force_close_error:
                                logger.error(f"Error force closing connection: {str(force_close_error)}")
                else:
                    logger.debug("Connection already closed or invalid")
            except Exception as e:
                logger.error(f"Error in connection cleanup: {str(e)}")
    except Exception as e:
        logger.error(f"Error in safe_close_connection: {str(e)}")

# Initialize the connection pool on module import
try:
    _connection_pool = init_db()
except Exception as e:
    logger.error(f"Failed to initialize connection pool on module import: {str(e)}")
    _connection_pool = None 