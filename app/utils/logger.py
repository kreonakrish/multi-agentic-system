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

# Default fields for workflow logging
DEFAULT_WORKFLOW_FIELDS = {
    'agent_id': '-',
    'team_id': '-',
    'task_id': '-',
    'correlation_id': '-',
    'task_type': '-',
    'knowledge_count': '-',
    'knowledge_relevance': '-',
    'memory_id': '-',
    'task_relevance': '-',
    'response_length': '-',
    'system_message_length': '-',
    'knowledge_integrated': '-',
    'matches_found': '-',
    'sample_match': '-'
}

# Create specialized loggers for different components
agent_logger = logging.getLogger('multi_agent_system.agent')
knowledge_retrieve_logger = logging.getLogger('multi_agent_system.knowledge.retrieve')
knowledge_llm_logger = logging.getLogger('multi_agent_system.knowledge.llm')
knowledge_metrics_logger = logging.getLogger('multi_agent_system.knowledge.metrics')

# Create workflow loggers with LoggerAdapter
workflow_logger = logging.LoggerAdapter(
    logging.getLogger('multi_agent_system.workflow'),
    DEFAULT_WORKFLOW_FIELDS
)

workflow_decision_logger = logging.LoggerAdapter(
    logging.getLogger('multi_agent_system.workflow.decisions'),
    DEFAULT_WORKFLOW_FIELDS
)

workflow_execution_logger = logging.LoggerAdapter(
    logging.getLogger('multi_agent_system.workflow.execution'),
    DEFAULT_WORKFLOW_FIELDS
)

workflow_steps_logger = logging.LoggerAdapter(
    logging.getLogger('multi_agent_system.workflow.steps'),
    DEFAULT_WORKFLOW_FIELDS
)

# Configure specialized loggers with appropriate log levels and handlers
specialized_loggers = [
    agent_logger,
    knowledge_retrieve_logger,
    knowledge_llm_logger,
    knowledge_metrics_logger,
    workflow_logger.logger,  # Access the underlying logger
    workflow_decision_logger.logger,
    workflow_execution_logger.logger,
    workflow_steps_logger.logger
]

for specialized_logger in specialized_loggers:
    # Inherit settings from main logger but ensure proper naming
    specialized_logger.propagate = True  # Allow propagation to parent logger
    specialized_logger.setLevel(logger.level)  # Inherit log level from main logger 