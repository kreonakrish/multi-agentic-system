import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from app.config.logging_config import configure_logging

# Configure the enhanced logging system
configure_logging()

# Get the logger for this module
logger = logging.getLogger('multi_agent_system')

# Note: For the log_execution decorator, use app.utils.decorators.log_execution instead