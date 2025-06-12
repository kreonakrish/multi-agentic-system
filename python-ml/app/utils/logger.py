import logging
import sys
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from app.config.logging_config import configure_logging

# Configure the enhanced logging system
configure_logging()

# Get the main logger for this module
logger = logging.getLogger('multi_agent_system')

# Create specialized loggers for different components
agent_logger = logging.getLogger('multi_agent_system.agent')
knowledge_retrieve_logger = logging.getLogger('multi_agent_system.knowledge.retrieve')
knowledge_llm_logger = logging.getLogger('multi_agent_system.knowledge.llm')
knowledge_metrics_logger = logging.getLogger('multi_agent_system.knowledge.metrics')

# Configure specialized loggers with appropriate log levels and handlers
for specialized_logger in [agent_logger, knowledge_retrieve_logger, knowledge_llm_logger, knowledge_metrics_logger]:
    # Inherit settings from main logger but ensure proper naming
    specialized_logger.propagate = True  # Allow propagation to parent logger
    specialized_logger.setLevel(logger.level)  # Inherit log level from main logger

# Note: For the log_execution decorator, use app.utils.decorators.log_execution instead