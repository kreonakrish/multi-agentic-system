import logging
import logging.handlers
import os
from typing import Optional

# Configure default logging format
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging(log_file: Optional[str] = 'app.log', log_level: int = logging.INFO) -> None:
    """
    Set up logging configuration for the application.
    Args:
        log_file: Path to the log file
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format=DEFAULT_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

# Create a logger instance for the application
logger = logging.getLogger('multi_agent_system')
logger.setLevel(logging.INFO) 