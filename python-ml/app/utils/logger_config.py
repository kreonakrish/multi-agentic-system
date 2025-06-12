def setup_logging():
    """Configure logging for the application."""
    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d |\n"
        "[Agent:%(agent_id)s Task:%(task_id)s Type:%(task_type)s]\n"
        "Message: %(message)s\n"
        "Details:\n"
        "  Task Description: %(task_description)s\n"
        "  Memory Count: %(memories_count)s\n"
        "  Memory Types: %(memory_types)s\n"
        "  Source Types: %(source_types)s\n"
        "  Confidence: %(avg_confidence).2f\n"
        "  Context: %(context_data)s\n"
        "Full Content:\n%(full_content)s\n"
        "-" * 80 + "\n"
    )

    # Create formatters and handlers
    formatter = logging.Formatter(
        log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Configure default values for log record attributes
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        
        # Set default values for all our custom fields
        record.agent_id = getattr(record, 'agent_id', '-')
        record.task_id = getattr(record, 'task_id', '-')
        record.task_type = getattr(record, 'task_type', '-')
        record.task_description = getattr(record, 'task_description', '-')
        record.memories_count = getattr(record, 'memories_count', 0)
        record.memory_types = getattr(record, 'memory_types', '[]')
        record.source_types = getattr(record, 'source_types', '[]')
        record.avg_confidence = getattr(record, 'avg_confidence', 0.0)
        record.context_data = getattr(record, 'context_data', '{}')
        record.full_content = getattr(record, 'full_content', '')
        
        return record

    logging.setLogRecordFactory(record_factory)

    # File handler
    log_file = os.path.join('logs', f'detailed_{datetime.now().strftime("%Y%m%d")}.log')
    os.makedirs('logs', exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Configure loggers
    loggers = [
        'multi_agent_system.knowledge.retrieve',
        'multi_agent_system.knowledge.llm',
        'multi_agent_system.knowledge.metrics',
        'multi_agent_system.agent',
        'multi_agent_system.workflow'
    ]

    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.propagate = False 