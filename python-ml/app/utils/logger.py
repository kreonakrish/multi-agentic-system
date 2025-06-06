import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

# Configure logger
logger = logging.getLogger('python-ml')
logger.setLevel(logging.DEBUG)

# Create formatters
console_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

file_formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] [%(pathname)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# File handler for all logs
log_file = os.path.join(logs_dir, f'python-ml-{datetime.now().strftime("%Y%m%d")}.log')
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# Error file handler
error_log_file = os.path.join(logs_dir, f'python-ml-error-{datetime.now().strftime("%Y%m%d")}.log')
error_file_handler = RotatingFileHandler(
    error_log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
error_file_handler.setLevel(logging.ERROR)
error_file_handler.setFormatter(file_formatter)
logger.addHandler(error_file_handler)

def log_execution(func):
    """Decorator to log function execution"""
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.info(f"\n[FUNCTION START] {func_name}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"[FUNCTION END] {func_name} - Completed successfully")
            return result
        except Exception as e:
            logger.error(f"[FUNCTION ERROR] {func_name} - Failed with error: {str(e)}", exc_info=True)
            raise
    return wrapper 