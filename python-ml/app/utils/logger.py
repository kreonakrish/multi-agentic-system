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
knowledge_store_logger = logging.getLogger('multi_agent_system.knowledge.store')
knowledge_llm_logger = logging.getLogger('multi_agent_system.knowledge.llm')
knowledge_metrics_logger = logging.getLogger('multi_agent_system.knowledge.metrics')
workflow_logger = logging.getLogger('multi_agent_system.workflow')
workflow_decision_logger = logging.getLogger('multi_agent_system.workflow.decisions')
workflow_execution_logger = logging.getLogger('multi_agent_system.workflow.execution')
workflow_steps_logger = logging.getLogger('multi_agent_system.workflow.steps')

# Configure specialized loggers with appropriate log levels and handlers
specialized_loggers = [
    agent_logger,
    knowledge_retrieve_logger,
    knowledge_store_logger,
    knowledge_llm_logger,
    knowledge_metrics_logger,
    workflow_logger,
    workflow_decision_logger,  # Workflow decision
    workflow_execution_logger,  # Workflow execution
    workflow_steps_logger  # Workflow steps
]

for specialized_logger in specialized_loggers:
    # Inherit settings from main logger but ensure proper naming
    specialized_logger.propagate = True  # Allow propagation to parent logger
    specialized_logger.setLevel(logger.level)  # Inherit log level from main logger
    
    # Add extra fields for workflow loggers
    if specialized_logger.name.startswith('multi_agent_system.workflow'):
        specialized_logger = logging.LoggerAdapter(specialized_logger, {
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
        })

# Note: For the log_execution decorator, use app.utils.decorators.log_execution instead