from functools import wraps
import time
from typing import Callable, Any
from app.utils.logger import logger

def log_execution(func: Callable) -> Callable:
    """
    Decorator to log function execution time and status.
    Args:
        func: The function to be decorated
    Returns:
        The wrapped function
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        func_name = func.__name__
        
        logger.info(f"Starting execution of {func_name}")
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Successfully completed {func_name} in {execution_time:.2f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error in {func_name} after {execution_time:.2f} seconds: {str(e)}")
            raise
    
    return wrapper 