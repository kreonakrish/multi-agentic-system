import os
import logging
import logging.handlers
from datetime import datetime
import json

class SafeFormatter(logging.Formatter):
    """Custom formatter that handles missing fields gracefully"""
    def format(self, record):
        # Add default values for our custom fields if they don't exist
        defaults = {
            'agent_id': '-',
            'team_id': '-',
            'correlation_id': '-',
            'funcName': record.funcName if hasattr(record, 'funcName') else '-',
            'lineno': record.lineno if hasattr(record, 'lineno') else '-',
            'openai_request': '-',
            'openai_response': '-',
            'endpoint': '-',
            'params': '-',
            'task_id': '-',
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
        
        # Add any missing keys to the record
        for key, default_value in defaults.items():
            if not hasattr(record, key):
                setattr(record, key, default_value)
        
        # Format any dict/list fields as JSON strings
        for field in ['openai_request', 'openai_response', 'params', 'knowledge_relevance']:
            value = getattr(record, field)
            if isinstance(value, (dict, list)):
                setattr(record, field, json.dumps(value, indent=2))
        
        return super().format(record)

def configure_logging():
    """Configure logging with detailed formatting and multiple handlers"""
    
    # Create logs directory if it doesn't exist
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create formatters using our SafeFormatter
    detailed_formatter = SafeFormatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d |\n'
        '[Agent:%(agent_id)s Team:%(team_id)s Task:%(task_id)s Correlation:%(correlation_id)s]\n'
        'Message: %(message)s\n'
        'Task Type: %(task_type)s\n'
        'Knowledge Count: %(knowledge_count)s\n'
        'Knowledge Relevance: %(knowledge_relevance)s\n'
        'Memory ID: %(memory_id)s\n'
        'Task Relevance: %(task_relevance)s\n'
        'Response Length: %(response_length)s\n'
        'System Message Length: %(system_message_length)s\n'
        'Knowledge Integrated: %(knowledge_integrated)s\n'
        'Matches Found: %(matches_found)s\n'
        'Sample Match: %(sample_match)s\n'
        'Endpoint: %(endpoint)s\n'
        'Parameters: %(params)s\n'
        'OpenAI Request: %(openai_request)s\n'
        'OpenAI Response: %(openai_response)s\n',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = SafeFormatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler for detailed logging
    detailed_file_handler = logging.FileHandler(
        os.path.join(log_dir, f'detailed_{datetime.now().strftime("%Y%m%d")}.log')
    )
    detailed_file_handler.setFormatter(detailed_formatter)
    detailed_file_handler.setLevel(logging.DEBUG)
    
    # File handler for general logging
    general_file_handler = logging.FileHandler(
        os.path.join(log_dir, f'general_{datetime.now().strftime("%Y%m%d")}.log')
    )
    general_file_handler.setFormatter(simple_formatter)
    general_file_handler.setLevel(logging.INFO)
    
    # Console handler with simple format
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(simple_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers
    root_logger.handlers = []
    
    # Add handlers
    root_logger.addHandler(detailed_file_handler)
    root_logger.addHandler(general_file_handler)
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    loggers_to_configure = [
        'multi_agent_system',
        'multi_agent_system.agent',
        'multi_agent_system.team',
        'multi_agent_system.task',
        'multi_agent_system.validation',
        'multi_agent_system.openai',
        'multi_agent_system.workflow',
        'multi_agent_system.workflow.steps',
        'multi_agent_system.workflow.execution',
        'multi_agent_system.workflow.decisions',
        'multi_agent_system.knowledge.retrieve',
        'multi_agent_system.knowledge.llm',
        'multi_agent_system.knowledge.metrics'
    ]
    
    for logger_name in loggers_to_configure:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        
        # Add handlers specific to this logger
        logger.handlers = []
        logger.addHandler(detailed_file_handler)
        logger.addHandler(general_file_handler)
        logger.addHandler(console_handler)
    
    # Log startup message
    startup_logger = logging.getLogger('multi_agent_system')
    startup_logger.info('Enhanced logging system initialized') 