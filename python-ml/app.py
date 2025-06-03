from flask import Flask, request, jsonify
from abc import ABC, abstractmethod
import mysql.connector
from mysql.connector import pooling
import os
from datetime import datetime, timedelta
import openai  # Changed from 'from openai import OpenAI'
from typing import Dict, Any, List, Optional
import json
from enum import Enum
from collections import defaultdict
import logging
import logging.handlers
from functools import wraps
import traceback
import uuid
import sys
from dotenv import load_dotenv
import decimal
import httpx

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize OpenAI client
try:
    if os.getenv('OPENAI_API_KEY'):
        logger.info('OPENAI_API_KEY found in environment')
        openai.api_key = os.getenv('OPENAI_API_KEY')  # Set the API key directly
    else:
        logger.error('OPENAI_API_KEY not found in environment')
        raise ValueError('OPENAI_API_KEY not found in environment')
except Exception as e:
    logger.error(f'Error initializing OpenAI client: {str(e)}')
    raise

def get_openai_client():
    """Get or initialize OpenAI client with proper error handling"""
    if not openai.api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        openai.api_key = api_key
    return openai

app = Flask(__name__)

def log_execution(f):
    """Decorator to add logging to API endpoints"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        correlation_id = str(uuid.uuid4())
        logger.info(
            f"Starting execution of {f.__name__}",
            extra={
                'correlation_id': correlation_id,
                'endpoint': f.__name__,
                'func_args': args,
                'func_kwargs': kwargs
            }
        )
        
        try:
            result = f(*args, **kwargs)
            logger.info(
                f"Completed execution of {f.__name__}",
                extra={
                    'correlation_id': correlation_id,
                    'endpoint': f.__name__,
                    'status': 'success'
                }
            )
            return result
        except Exception as e:
            logger.error(
                f"Error in {f.__name__}: {str(e)}",
                extra={
                    'correlation_id': correlation_id,
                    'endpoint': f.__name__,
                    'error_msg': str(e),
                    'traceback': traceback.format_exc()
                }
            )
            raise
    return wrapper

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'admin',
    'password': 'gUest@Sep2',
    'database': 'multi_agentic_system',
    'pool_name': 'mypool',
    'pool_size': 20,  # Increased from 5 to 20
    'pool_reset_session': True,
    'connect_timeout': 10
}

# Create connection pool with better error handling and monitoring
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)
    logger.info("Database connection pool initialized successfully with size: %d", db_config['pool_size'])
except mysql.connector.Error as e:
    logger.error(f"Error creating connection pool: {e}", exc_info=True)
    raise

def get_db_connection():
    """Get a connection from the pool with proper error handling and monitoring"""
    try:
        conn = connection_pool.get_connection()
        logger.debug("Got connection from pool")
        # Configure connection after getting it from pool
        conn.set_charset_collation('utf8mb4', 'utf8mb4_unicode_ci')
        conn.autocommit = True
        return conn
    except mysql.connector.errors.PoolError as e:
        logger.error(f"Pool error getting connection: {e}", exc_info=True)
        # Try to clean up any stale connections
        try:
            connection_pool._remove_connections()
            conn = connection_pool.get_connection()
            conn.set_charset_collation('utf8mb4', 'utf8mb4_unicode_ci')
            conn.autocommit = True
            logger.info("Successfully got connection after pool cleanup")
            return conn
        except Exception as cleanup_error:
            logger.error(f"Failed to cleanup pool and get new connection: {cleanup_error}", exc_info=True)
            raise
    except mysql.connector.Error as e:
        logger.error(f"Error getting database connection: {e}", exc_info=True)
        raise

def safe_close_connection(conn, cursor=None):
    """Safely close cursor and connection with proper error handling"""
    try:
        if cursor:
            cursor.close()
            logger.debug("Cursor closed successfully")
    except Exception as e:
        logger.warning(f"Error closing cursor: {e}")

    try:
        if conn:
            if not conn.in_transaction:  # Only return connection to pool if not in transaction
                conn.close()
                logger.debug("Connection returned to pool successfully")
            else:
                logger.warning("Connection has uncommitted transaction, rolling back before return to pool")
                conn.rollback()
                conn.close()
    except Exception as e:
        logger.warning(f"Error returning connection to pool: {e}")
        try:
            # Force close if normal close fails
            if conn:
                conn._force_close()
                logger.info("Connection force closed")
        except Exception as force_close_error:
            logger.error(f"Error force closing connection: {force_close_error}")

class Tool(ABC):
    def __init__(self, tool_id, tool_name, hostname, username, password, auth_method):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.hostname = hostname
        self.username = username
        self.password = password
        self.auth_method = auth_method

    def connect(self):
        """Base connect method that always returns True for now"""
        return True

    def get_default_response(self, command):
        """Get a structured default response for the tool"""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "tool_type": self.__class__.__name__,
            "hostname": self.hostname,
            "auth_method": self.auth_method,
            "command": command,
            "status": "success",
            "message": f"Agent has successfully used the {self.tool_name} ({self.__class__.__name__})"
        }

    def execute(self, command):
        """Base execute method that returns a default response"""
        return self.get_default_response(command)

class DatabaseTool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "database_specific": {
                "query_type": "simulated",
                "affected_rows": 0,
                "execution_time": "0.00s"
            }
        })
        return response

class APITool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "api_specific": {
                "endpoint": f"{self.hostname}/api/v1/simulate",
                "method": "GET",
                "response_time": "0.00s"
            }
        })
        return response

class WebServiceTool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "service_specific": {
                "service_endpoint": f"{self.hostname}/service/simulate",
                "service_type": "REST",
                "response_time": "0.00s"
            }
        })
        return response

class InteractionType(Enum):
    DIRECT = "direct"
    WORKFLOW = "workflow"
    BROADCAST = "broadcast"
    CHAIN = "chain"

class InteractionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentInteraction:
    def __init__(self, 
                 interaction_id: int,
                 source_agent_id: int,
                 target_agent_id: int,
                 interaction_type: str,
                 message: str,
                 status: str = InteractionStatus.PENDING.value):
        self.interaction_id = interaction_id
        self.source_agent_id = source_agent_id
        self.target_agent_id = target_agent_id
        self.interaction_type = interaction_type
        self.message = message
        self.status = status
        self.response = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "interaction_type": self.interaction_type,
            "message": self.message,
            "status": self.status,
            "response": self.response,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class TeamPermission:
    def __init__(self, team_id: int, tool_id: int, permission_level: str):
        self.team_id = team_id
        self.tool_id = tool_id
        self.permission_level = permission_level  # read, write, admin

class TeamConfig:
    def __init__(self, team_id: int, name: str, config_data: Dict[str, Any]):
        self.team_id = team_id
        self.name = name
        self.config_data = config_data
        self.permissions = []
        self.metrics = TeamMetrics(team_id)

    def add_permission(self, tool_id: int, permission_level: str):
        self.permissions.append(TeamPermission(self.team_id, tool_id, permission_level))

    def has_permission(self, tool_id: int, required_level: str) -> bool:
        for perm in self.permissions:
            if perm.tool_id == tool_id:
                if required_level == 'read' and perm.permission_level in ['read', 'write', 'admin']:
                    return True
                if required_level == 'write' and perm.permission_level in ['write', 'admin']:
                    return True
                if required_level == 'admin' and perm.permission_level == 'admin':
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "config": self.config_data,
            "permissions": [
                {
                    "tool_id": p.tool_id,
                    "level": p.permission_level
                } for p in self.permissions
            ]
        }

class TeamMetrics:
    def __init__(self, team_id: int):
        self.team_id = team_id
        self.interaction_counts = defaultdict(int)
        self.tool_usage = defaultdict(int)
        self.success_rate = defaultdict(float)
        self.response_times = defaultdict(list)
        self.last_updated = datetime.now()

    def update_metrics(self, metric_type: str, value: Any):
        if metric_type == "interaction":
            self.interaction_counts[value] += 1
        elif metric_type == "tool_usage":
            self.tool_usage[value] += 1
        elif metric_type == "success_rate":
            self.success_rate[value[0]] = value[1]
        elif metric_type == "response_time":
            self.response_times[value[0]].append(value[1])
        
        self.last_updated = datetime.now()

    def get_metrics(self, time_range: str = "24h") -> Dict[str, Any]:
        cutoff = datetime.now()
        if time_range == "24h":
            cutoff = cutoff - timedelta(hours=24)
        elif time_range == "7d":
            cutoff = cutoff - timedelta(days=7)
        elif time_range == "30d":
            cutoff = cutoff - timedelta(days=30)

        return {
            "team_id": self.team_id,
            "interaction_counts": dict(self.interaction_counts),
            "tool_usage": dict(self.tool_usage),
            "success_rate": dict(self.success_rate),
            "average_response_times": {
                tool_id: sum(times)/len(times) if times else 0 
                for tool_id, times in self.response_times.items()
            },
            "last_updated": self.last_updated.isoformat()
        }

class Agent:
    def __init__(self, agent_id: int, name: str, memory_type: str, foundation_model: str, team_id: Optional[int] = None, use_prod: bool = False):
        self.agent_id = agent_id
        self.name = name
        self.memory_type = memory_type
        self.foundation_model = foundation_model
        self.use_prod = use_prod
        self.team_id = team_id
        self.team_config = None
        self.tools = []
        self.memories = []
        self.pending_interactions = []
        self.interaction_history = []
        self.correlation_id = None
        self.logger = logging.getLogger(f'multi_agent_system.agent.{agent_id}')

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for tracking agent actions"""
        self.correlation_id = correlation_id

    def log(self, level: str, message: str, **kwargs):
        """Structured logging for agent actions"""
        extra = {
            'correlation_id': self.correlation_id or 'NO_CORRELATION_ID',
            'agent_id': self.agent_id,
            'agent_name': self.name,
            'team_id': self.team_id,
            **kwargs
        }
        getattr(self.logger, level)(message, extra=extra)

    def load_team_config(self, cursor) -> bool:
        """Load team configuration and permissions"""
        if not self.team_id:
            return False

        # Get team details
        cursor.execute("SELECT * FROM teams WHERE id = %s", (self.team_id,))
        team_data = cursor.fetchone()
        if not team_data:
            return False

        # Get team configuration
        cursor.execute("SELECT * FROM team_configurations WHERE team_id = %s", (self.team_id,))
        config_data = cursor.fetchone() or {}

        # Create team config
        self.team_config = TeamConfig(self.team_id, team_data['name'], config_data)

        # Load team permissions
        cursor.execute("""
            SELECT tool_id, permission_level 
            FROM team_permissions 
            WHERE team_id = %s
        """, (self.team_id,))
        
        permissions = cursor.fetchall()
        for perm in permissions:
            self.team_config.add_permission(perm['tool_id'], perm['permission_level'])

        return True

    def check_tool_permission(self, tool_id: int, required_level: str) -> bool:
        """Check if the agent's team has required permission for the tool"""
        if not self.team_config:
            return False
        return self.team_config.has_permission(tool_id, required_level)

    def update_team_metrics(self, metric_type: str, value: Any):
        """Update team metrics"""
        if self.team_config and self.team_config.metrics:
            self.team_config.metrics.update_metrics(metric_type, value)

    def execute_with_tool(self, tool_id: int, command: str) -> Dict[str, Any]:
        """Execute command with permission check, metrics tracking, and logging"""
        self.log('info', 'Starting tool execution', tool_id=tool_id, command=command)
        
        # Check permissions
        if not self.check_tool_permission(tool_id, 'write'):
            self.log('warning', 'Permission denied for tool execution', 
                    tool_id=tool_id, required_permission='write')
            return {"status": "error", "message": "Insufficient permissions for this tool"}

        start_time = datetime.now()
        try:
            result = super().execute_with_tool(tool_id, command)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log execution result
            self.log('info', 'Tool execution completed',
                    tool_id=tool_id,
                    execution_time=execution_time,
                    status=result["status"])

            # Update metrics
            if self.team_config:
                self.update_team_metrics("tool_usage", tool_id)
                self.update_team_metrics("response_time", (tool_id, execution_time))
                self.update_team_metrics("success_rate", 
                    (tool_id, 1.0 if result["status"] == "success" else 0.0))

            return result
        except Exception as e:
            self.log('error', f'Tool execution failed: {str(e)}',
                    tool_id=tool_id,
                    error=str(e),
                    traceback=traceback.format_exc())
            raise

    def add_tool(self, tool):
        self.tools.append(tool)

    def remove_tool(self, tool_id):
        self.tools = [t for t in self.tools if t.tool_id != tool_id]

    def load_memories(self, cursor):
        """Load agent's memories from database"""
        cursor.execute("""
            SELECT * FROM agent_memory 
            WHERE agent_id = %s 
            ORDER BY updated_at DESC
        """, (self.agent_id,))
        self.memories = cursor.fetchall()
        return self.memories

    def get_context_from_memories(self):
        """Get relevant context from agent's memories"""
        if not self.memories:
            return ""
        
        # Get the most recently updated memory
        latest_memory = self.memories[0]
        context = []
        
        if latest_memory['start_prompt']:
            context.append(f"Start Prompt: {latest_memory['start_prompt']}")
        if latest_memory['context']:
            context.append(f"Context: {latest_memory['context']}")
        if latest_memory['end_prompt']:
            context.append(f"End Prompt: {latest_memory['end_prompt']}")
        
        return "\n".join(context)

    def process_with_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Process messages with the appropriate LLM (OpenAI by default, or production model if specified)
        """
        if self.use_prod:
            # TODO: Implement production model integration
            return {"status": "error", "message": "Production model not implemented yet"}
        
        try:
            # Get OpenAI client with error handling
            try:
                openai_client = get_openai_client()
            except ValueError as e:
                self.log('error', f"OpenAI client initialization failed: {str(e)}")
                return {"status": "error", "message": str(e)}
            
            # Log the request
            self.log('info', "Sending request to OpenAI API...", 
                    extra={'messages': messages})

            # Store the message in database before sending to OpenAI
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                # Store initial message
                conversation_id = str(uuid.uuid4())
                insert_query = """
                    INSERT INTO messages 
                    (sender_id, receiver_id, content, interaction_type, conversation_id, team_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                # Get the user message (last message in the list)
                user_message = next((msg['content'] for msg in reversed(messages) if msg['role'] == 'user'), None)
                if not user_message:
                    user_message = messages[-1]['content']
                
                cursor.execute(insert_query, (
                    self.agent_id,  # sender_id (agent sending to OpenAI)
                    None,  # receiver_id (OpenAI doesn't have an ID)
                    user_message,
                    'foundation_model',
                    conversation_id,
                    self.team_id,
                    'pending'
                ))
                
                conn.commit()
            except Exception as db_error:
                self.log('error', f"Database error storing initial message: {str(db_error)}")
                if conn:
                    conn.rollback()
            finally:
                safe_close_connection(conn, cursor)
            
            # Use OpenAI's chat completion
            try:
                response = openai_client.ChatCompletion.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                self.log('info', "Received response from OpenAI API")
                self.log('debug', f"Model response: {response.choices[0].message['content']}")
                
                # Store OpenAI's response in database
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor(dictionary=True)
                    
                    # Store OpenAI's response
                    insert_query = """
                        INSERT INTO messages 
                        (sender_id, receiver_id, content, interaction_type, conversation_id, team_id, status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_query, (
                        None,  # sender_id (OpenAI sending to agent)
                        self.agent_id,  # receiver_id
                        response.choices[0].message['content'],
                        'foundation_model',
                        conversation_id,
                        self.team_id,
                        'processed'
                    ))
                    
                    conn.commit()
                except Exception as db_error:
                    self.log('error', f"Database error storing OpenAI response: {str(db_error)}")
                    if conn:
                        conn.rollback()
                finally:
                    safe_close_connection(conn, cursor)
                
                return {
                    "status": "success",
                    "response": response.choices[0].message['content'],
                    "model_used": "gpt-4",
                    "conversation_id": conversation_id
                }
            except openai.error.RateLimitError as e:
                self.log('error', "OpenAI API rate limit exceeded", exc_info=True)
                return {
                    "status": "error",
                    "message": "Rate limit exceeded. Please try again later.",
                    "error_type": "rate_limit"
                }
            except openai.error.APIError as e:
                self.log('error', f"OpenAI API error: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"OpenAI API error: {str(e)}",
                    "error_type": "api_error"
                }
            except Exception as e:
                self.log('error', f"Unexpected error in OpenAI API call: {str(e)}", exc_info=True)
                return {
                    "status": "error",
                    "message": f"Unexpected error: {str(e)}",
                    "details": traceback.format_exc()
                }
                
        except Exception as e:
            self.log('error', f"Error in process_with_llm: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error processing with LLM: {str(e)}",
                "details": traceback.format_exc()
            }

    def format_messages_for_llm(self, command: str, context: str = "") -> List[Dict[str, str]]:
        """
        Format the command and context into messages for the LLM
        """
        messages = []
        
        # Add system message with agent context
        system_msg = f"You are {self.name}, an AI agent with {self.memory_type} memory type. "
        if self.tools:
            tool_names = [t.tool_name for t in self.tools]
            system_msg += f"You have access to the following tools: {', '.join(tool_names)}."
        messages.append({"role": "system", "content": system_msg})
        
        # Add context from memories if available
        if context:
            messages.append({"role": "system", "content": f"Previous context:\n{context}"})
        
        # Add the actual command
        messages.append({"role": "user", "content": command})
        
        return messages

    def validate_response_with_llm(self, response: str, end_prompt: str) -> Dict[str, Any]:
        """
        Validate if the response satisfies the end prompt using the foundation model
        """
        validation_messages = [
            {
                "role": "system",
                "content": "You are a validation agent. Your task is to verify if the given response satisfies the end prompt requirements. Return a JSON with format: {\"valid\": boolean, \"reason\": string}"
            },
            {
                "role": "user",
                "content": f"End Prompt Requirements:\n{end_prompt}\n\nResponse to Validate:\n{response}\n\nDoes this response satisfy the end prompt requirements? Provide your assessment in the required JSON format."
            }
        ]

        try:
            validation_response = get_openai_client().chat.completions.create(
                model="gpt-4",
                messages=validation_messages,
                temperature=0.3,  # Lower temperature for more consistent validation
                max_tokens=500
            )
            
            validation_result = validation_response.choices[0].message.content
            # Extract the JSON part from the response
            try:
                validation_json = json.loads(validation_result)
                return {
                    "status": "success",
                    "valid": validation_json.get("valid", False),
                    "reason": validation_json.get("reason", "No reason provided")
                }
            except json.JSONDecodeError:
                return {
                    "status": "error",
                    "message": "Failed to parse validation response",
                    "raw_response": validation_result
                }
                
        except Exception as e:
            return {"status": "error", "message": f"Validation failed: {str(e)}"}

    def execute_with_tools(self, command: str) -> Dict[str, Any]:
        """Execute command with all configured tools"""
        self.log('info', f"[execute_with_tools] Starting execution with command: {command}")
        
        if not self.tools:
            self.log('warning', "[execute_with_tools] No tools configured for this agent")
            return {"status": "error", "message": "No tools configured for this agent"}

        try:
            # Get context from memories
            self.log('info', "[execute_with_tools] Getting context from memories")
            context = self.get_context_from_memories()
            end_prompt = None
            if self.memories and self.memories[0].get('end_prompt'):
                end_prompt = self.memories[0]['end_prompt']
            self.log('debug', f"[execute_with_tools] Retrieved context: {context}, end_prompt: {end_prompt}")

            # Process command with LLM first
            self.log('info', "[execute_with_tools] Processing command with LLM")
            messages = self.format_messages_for_llm(command, context)
            self.log('debug', f"[execute_with_tools] Formatted messages for LLM: {messages}")
            
            llm_response = self.process_with_llm(messages)
            self.log('info', f"[execute_with_tools] LLM processing status: {llm_response['status']}")
            
            if llm_response["status"] != "success":
                self.log('error', f"[execute_with_tools] LLM processing failed: {llm_response}")
                return llm_response

            # Store agent-to-agent interactions if this is part of a team task
            try:
                if isinstance(command, str) and command.startswith('{') and command.endswith('}'):
                    # This is likely a team task message
                    task_data = json.loads(command)
                    if 'task_description' in task_data and 'conversation_context' in task_data:
                        conn = get_db_connection()
                        cursor = conn.cursor(dictionary=True)
                        
                        # Get the last agent from conversation context
                        last_agent = None
                        if task_data['conversation_context']:
                            last_agent = task_data['conversation_context'][-1].get('agent_id')
                        
                        # Store the interaction
                        insert_query = """
                            INSERT INTO messages 
                            (sender_id, receiver_id, content, processed_message, model_response, 
                             interaction_type, conversation_id, team_id, status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                        
                        cursor.execute(insert_query, (
                            last_agent,  # sender_id (previous agent or NULL if first)
                            self.agent_id,  # receiver_id (current agent)
                            json.dumps(task_data),  # content
                            llm_response.get("response", ""),  # processed_message
                            json.dumps(llm_response),  # model_response
                            'team_task',  # interaction_type
                            llm_response.get("conversation_id"),  # conversation_id
                            self.team_id,  # team_id
                            'processed'  # status
                        ))
                        
                        conn.commit()
                        safe_close_connection(conn, cursor)
            except Exception as db_error:
                self.log('error', f"[execute_with_tools] Database error storing team interaction: {str(db_error)}")
                # Continue execution even if storage fails

            # Execute command with all tools
            self.log('info', "[execute_with_tools] Executing command with tools")
            tool_responses = []
            for tool in self.tools:
                try:
                    self.log('info', f"[execute_with_tools] Executing with tool: {tool.tool_name}")
                    result = tool.execute(llm_response["response"])
                    tool_responses.append(result)
                    self.log('debug', f"[execute_with_tools] Tool response: {result}")
                except Exception as tool_error:
                    self.log('error', f"[execute_with_tools] Error executing tool {tool.tool_name}: {str(tool_error)}", exc_info=True)
                    tool_responses.append({
                        "status": "error",
                        "tool_name": tool.tool_name,
                        "error": str(tool_error)
                    })

            # Check if all tool executions failed
            if all(response.get("status") == "error" for response in tool_responses):
                self.log('error', "[execute_with_tools] All tool executions failed")
                return {
                    "status": "error",
                    "message": "All tool executions failed",
                    "tool_responses": tool_responses
                }

            # Validate responses if end prompt exists
            validation_results = []
            if end_prompt:
                self.log('info', "[execute_with_tools] Validating responses against end prompt")
                for response in tool_responses:
                    try:
                        validation_result = self.validate_response_with_llm(
                            str(response),  # Convert response to string for validation
                            end_prompt
                        )
                        validation_results.append(validation_result)
                        self.log('debug', f"[execute_with_tools] Validation result: {validation_result}")
                    except Exception as validation_error:
                        self.log('error', f"[execute_with_tools] Error validating response: {str(validation_error)}", exc_info=True)
                        validation_results.append({
                            "status": "error",
                            "message": f"Validation failed: {str(validation_error)}"
                        })

            # Compile final response
            final_response = {
                "status": "success",
                "context": context,
                "memory_type": self.memory_type,
                "llm_response": llm_response["response"],
                "model_used": llm_response["model_used"],
                "conversation_id": llm_response.get("conversation_id"),
                "tool_responses": tool_responses,
                "validation_results": validation_results if end_prompt else None
            }
            
            self.log('info', "[execute_with_tools] Successfully completed execution")
            return final_response

        except Exception as e:
            self.log('error', f"[execute_with_tools] Unhandled error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Error executing command: {str(e)}",
                "details": traceback.format_exc()
            }

    def execute_with_tool(self, tool_id: int, command: str) -> Dict[str, Any]:
        """Legacy method for single tool execution"""
        tool = next((t for t in self.tools if t.tool_id == tool_id), None)
        if not tool:
            return {"status": "error", "message": "Tool not found"}
        
        # Get context from memories
        context = self.get_context_from_memories()
        end_prompt = None
        if self.memories and self.memories[0].get('end_prompt'):
            end_prompt = self.memories[0]['end_prompt']
        
        if tool.connect():
            messages = self.format_messages_for_llm(command, context)
            llm_response = self.process_with_llm(messages)
            
            if llm_response["status"] != "success":
                return llm_response
            
            result = tool.execute(llm_response["response"])
            
            validation_result = None
            if end_prompt and result["status"] == "success":
                validation_result = self.validate_response_with_llm(
                    str(result),
                    end_prompt
                )
                
                if validation_result["status"] == "success" and not validation_result["valid"]:
                    result["validation_warning"] = validation_result["reason"]
            
            result.update({
                "context": context,
                "memory_type": self.memory_type,
                "llm_response": llm_response["response"],
                "model_used": llm_response["model_used"],
                "validation_result": validation_result
            })
            
            return result
        return {"status": "error", "message": "Failed to connect to tool"}

    def send_message(self, target_agent_id: int, message: str, interaction_type: str = InteractionType.DIRECT.value) -> Dict[str, Any]:
        """Send a message to another agent with logging"""
        self.log('info', 'Sending message to agent',
                target_agent_id=target_agent_id,
                interaction_type=interaction_type)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Create new interaction
            cursor.execute("""
                INSERT INTO agent_interactions 
                (source_agent_id, target_agent_id, interaction_type, message, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (self.agent_id, target_agent_id, interaction_type, message, InteractionStatus.PENDING.value))
            
            interaction_id = cursor.lastrowid
            conn.commit()

            # Create interaction object
            interaction = AgentInteraction(
                interaction_id,
                self.agent_id,
                target_agent_id,
                interaction_type,
                message
            )

            # Process the message with LLM before sending
            messages = self.format_messages_for_llm(
                f"Process this message for agent {target_agent_id}: {message}",
                context=self.get_context_from_memories()
            )
            llm_response = self.process_with_llm(messages)

            if llm_response["status"] == "success":
                processed_message = llm_response["response"]
                
                # Update interaction with processed message
                cursor.execute("""
                    UPDATE agent_interactions 
                    SET processed_message = %s,
                        status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (processed_message, InteractionStatus.IN_PROGRESS.value, interaction_id))
                conn.commit()

                interaction.message = processed_message
                interaction.status = InteractionStatus.IN_PROGRESS.value

            cursor.close()
            conn.close()

            self.log('info', 'Message sent successfully',
                    target_agent_id=target_agent_id,
                    interaction_id=interaction.interaction_id)
            
            return {
                "status": "success",
                "interaction": interaction.to_dict(),
                "llm_response": llm_response.get("response")
            }

        except Exception as e:
            self.log('error', f'Failed to send message: {str(e)}',
                    target_agent_id=target_agent_id,
                    error=str(e),
                    traceback=traceback.format_exc())
            raise

    def receive_message(self, interaction_id: int) -> Dict[str, Any]:
        """Process a received message"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get interaction details
            cursor.execute("""
                SELECT id, source_agent_id, target_agent_id, message, processed_message, created_at, updated_at
                FROM agent_interactions 
                WHERE id = %s AND target_agent_id = %s
            """, (interaction_id, self.agent_id))
            
            interaction = cursor.fetchone()
            if not interaction:
                return jsonify({
                    'status': 'error',
                    'message': 'Interaction not found'
                }), 404
            
            # Convert datetime objects to strings for JSON serialization
            if interaction:
                for key in ['created_at', 'updated_at']:
                    if key in interaction and interaction[key]:
                        if isinstance(interaction[key], datetime):
                            interaction[key] = interaction[key].isoformat()
                        else:
                            interaction[key] = str(interaction[key])
            
            # Update interaction status
            cursor.execute("""
                UPDATE agent_interactions 
                SET processed_message = message,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (interaction_id,))
            
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'interaction': interaction
            })
            
        except Exception as e:
            logger.error(f"Error receiving message: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()

    def start_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a multi-agent workflow"""
        try:
            workflow_type = workflow_data.get("type", "sequential")
            agents = workflow_data.get("agents", [])
            message = workflow_data.get("message", "")

            if not agents:
                return {"status": "error", "message": "No agents specified for workflow"}

            if workflow_type == "sequential":
                return self._start_sequential_workflow(agents, message)
            elif workflow_type == "broadcast":
                return self._start_broadcast_workflow(agents, message)
            else:
                return {"status": "error", "message": f"Unsupported workflow type: {workflow_type}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _start_sequential_workflow(self, agents: List[int], message: str) -> Dict[str, Any]:
        """Start a sequential workflow where agents process in sequence"""
        try:
            interactions = []
            current_message = message

            for i, target_agent_id in enumerate(agents):
                # Send message to next agent in sequence
                result = self.send_message(
                    target_agent_id,
                    current_message,
                    InteractionType.WORKFLOW.value
                )

                if result["status"] != "success":
                    return result

                interactions.append(result["interaction"])
                current_message = result["llm_response"]

            return {
                "status": "success",
                "workflow_type": "sequential",
                "interactions": interactions
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _start_broadcast_workflow(self, agents: List[int], message: str) -> Dict[str, Any]:
        """Start a broadcast workflow where message is sent to all agents simultaneously"""
        try:
            interactions = []

            for target_agent_id in agents:
                result = self.send_message(
                    target_agent_id,
                    message,
                    InteractionType.BROADCAST.value
                )

                if result["status"] == "success":
                    interactions.append(result["interaction"])

            return {
                "status": "success",
                "workflow_type": "broadcast",
                "interactions": interactions
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

class TeamTask:
    def __init__(self, task_id: str, description: str, requirements: Dict[str, Any]):
        self.task_id = task_id
        self.description = description
        self.requirements = requirements
        self.status = "pending"
        self.results = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "requirements": self.requirements,
            "status": self.status,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class TeamMember:
    def __init__(self, agent_id: int, priority: int, accuracy_threshold: float, success_rate: float):
        self.agent_id = agent_id
        self.priority = priority
        self.accuracy_threshold = accuracy_threshold
        self.success_rate = success_rate
        self.current_task = None
        self.results = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "priority": self.priority,
            "accuracy_threshold": self.accuracy_threshold,
            "success_rate": self.success_rate,
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "results": self.results
        }

class Team:
    def __init__(self, team_id: str, name: str, description: str):
        self.team_id = team_id
        self.name = name
        self.description = description
        self.members: List[TeamMember] = []
        self.tasks: List[TeamTask] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_member(self, member: TeamMember):
        self.members.append(member)
        # Sort members by priority (highest first)
        self.members.sort(key=lambda x: x.priority, reverse=True)

    def assign_task(self, task: TeamTask):
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "members": [member.to_dict() for member in self.members],
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

def create_tool(tool_data):
    tool_types = {
        "Database": DatabaseTool,
        "API": APITool,
        "WebService": WebServiceTool
    }
    
    tool_class = tool_types.get(tool_data["tool_type"])
    if not tool_class:
        raise ValueError(f"Unknown tool type: {tool_data['tool_type']}")
    
    return tool_class(
        tool_data["id"],
        tool_data["tool_name"],
        tool_data["hostname"],
        tool_data["username"],
        tool_data["password"],
        tool_data["auth_method"]
    )

@app.route('/api/ml/agent/<int:agent_id>/initialize', methods=['POST'])
def initialize_agent(agent_id):
    try:
        data = request.get_json()
        use_prod = data.get('use_prod', False)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get agent details with correct column names
        cursor.execute("""
            SELECT id, name, memory_type, foundation_model, status 
            FROM agents WHERE id = %s
        """, (agent_id,))
        agent_data = cursor.fetchone()
        
        if not agent_data:
            return jsonify({
                'status': 'error',
                'message': f'Agent {agent_id} not found'
            }), 404
        
        # Update agent status to active
        cursor.execute(
            "UPDATE agents SET status = 'active' WHERE id = %s",
            (agent_id,)
        )
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Agent {agent_id} initialized successfully',
            'agent': {
                'id': agent_data[0],
                'name': agent_data[1],
                'memory_type': agent_data[2],
                'foundation_model': agent_data[3],
                'status': 'active'
            }
        })
        
    except Exception as e:
        logger.error(f"Error initializing agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/send', methods=['POST'])
@log_execution
def send_agent_message(agent_id):
    """Send a message to an agent and get response from foundation model"""
    conn = None
    cursor = None
    try:
        # Log request data
        request_data = request.get_json()
        logger.info(f"[send_agent_message] Received request data: {request_data}")
        
        message = request_data.get('message')
        team_id = request_data.get('team_id')
        interaction_type = request_data.get('interaction_type', 'direct')

        if not message:
            logger.warning("[send_agent_message] Message is required")
            return jsonify({
                "status": "error",
                "message": "message is required"
            }), 400

        # Initialize agent
        logger.info(f"[send_agent_message] Initializing agent {agent_id} from database...")
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            logger.error(f"[send_agent_message] Agent {agent_id} not found in database")
            return jsonify({"status": "error", "message": "Agent not found"}), 404

        # Log agent details
        logger.info(f"[send_agent_message] Agent details: id={agent.agent_id}, name={agent.name}, memory_type={agent.memory_type}")
        logger.info(f"[send_agent_message] Agent tools: {[t.tool_name for t in agent.tools]}")

        # Set correlation ID for tracking
        conversation_id = str(uuid.uuid4())
        agent.set_correlation_id(conversation_id)
        logger.info(f"[send_agent_message] Set conversation ID: {conversation_id}")

        # Store the message in database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            logger.info("[send_agent_message] Storing initial message in database...")
            
            # First verify we can insert
            cursor.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
            if not cursor.fetchone():
                raise ValueError(f"Agent {agent_id} not found in database")
            
            # Insert the message
            insert_query = """
                INSERT INTO messages 
                (sender_id, receiver_id, content, interaction_type, conversation_id, team_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            insert_values = (None, agent_id, message, interaction_type, conversation_id, team_id, 'pending')
            
            logger.info(f"[send_agent_message] Executing insert with values: {insert_values}")
            cursor.execute(insert_query, insert_values)
            
            # Get the inserted ID
            message_id = cursor.lastrowid
            logger.info(f"[send_agent_message] Message inserted with ID: {message_id}")
            
            # Verify the insert
            cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
            inserted_message = cursor.fetchone()
            if not inserted_message:
                raise ValueError("Message insert failed - no row found after insert")
                
            conn.commit()
            logger.info("[send_agent_message] Message stored and committed successfully")
            
        except Exception as db_error:
            if conn:
                conn.rollback()
            logger.error(f"[send_agent_message] Database error storing message: {str(db_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Database error: {str(db_error)}"
            }), 500
        finally:
            safe_close_connection(conn, cursor)

        # Process with foundation model
        logger.info("[send_agent_message] Processing message with foundation model...")
        try:
            # Log the messages being sent to the model
            formatted_messages = agent.format_messages_for_llm(message)
            logger.info(f"[send_agent_message] Formatted messages for LLM: {formatted_messages}")
            
            # Log agent state before execution
            logger.info(f"[send_agent_message] Agent state before execution: memories={len(agent.memories)}, tools={len(agent.tools)}")
            
            result = agent.execute_with_tools(message)
            logger.info("[send_agent_message] Foundation model processing complete")
            logger.debug(f"[send_agent_message] Model result: {result}")
            
            if result.get('status') != 'success':
                logger.error(f"[send_agent_message] Model processing failed: {result}")
                return jsonify(result), 500
                
        except Exception as model_error:
            logger.error(f"[send_agent_message] Error processing with foundation model: {str(model_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Model processing error: {str(model_error)}",
                "details": traceback.format_exc()
            }), 500
        
        # Store the model's response
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            logger.info("[send_agent_message] Storing model response in database...")
            update_query = """
                UPDATE messages 
                SET processed_message = %s,
                    model_response = %s,
                    status = 'processed'
                WHERE conversation_id = %s
            """
            update_values = (
                result.get('llm_response', ''),
                json.dumps(result),
                conversation_id
            )
            
            logger.info(f"[send_agent_message] Executing update with values: {update_values}")
            cursor.execute(update_query, update_values)
            
            # Verify the update
            cursor.execute("SELECT * FROM messages WHERE conversation_id = %s", (conversation_id,))
            updated_message = cursor.fetchone()
            if not updated_message or updated_message['status'] != 'processed':
                raise ValueError("Message update failed - no row found or status not updated")
                
            conn.commit()
            logger.info("[send_agent_message] Model response stored and committed successfully")
            
        except Exception as db_error:
            if conn:
                conn.rollback()
            logger.error(f"[send_agent_message] Database error storing model response: {str(db_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Database error: {str(db_error)}",
                "details": traceback.format_exc()
            }), 500
        finally:
            safe_close_connection(conn, cursor)

        response_data = {
            "status": "success",
            "conversation_id": conversation_id,
            "model_response": result.get('llm_response', ''),
            "full_response": result
        }
        logger.info("[send_agent_message] Successfully completed message processing")
        return jsonify(response_data)

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"[send_agent_message] Unhandled error: {str(e)}",
            extra={
                'agent_id': agent_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({
            "status": "error",
            "message": f"Error processing message: {str(e)}",
            "details": traceback.format_exc()
        }), 500
    finally:
        safe_close_connection(conn, cursor)

@app.route('/api/ml/agent/<int:agent_id>/response/<conversation_id>', methods=['GET'])
@log_execution
def get_agent_response(agent_id, conversation_id):
    """Get the foundation model's response for a specific conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                """SELECT content, processed_message, model_response, status
                FROM messages 
                WHERE conversation_id = %s AND receiver_id = %s""",
                (conversation_id, agent_id)
            )
            message = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not message:
            return jsonify({
                "status": "error",
                "message": "Message not found"
            }), 404

        if message['status'] != 'processed':
            return jsonify({
                "status": "pending",
                "message": "Message is still being processed"
            })

        return jsonify({
            "status": "success",
            "original_message": message['content'],
            "model_response": message['processed_message'],
            "full_response": json.loads(message['model_response']) if message['model_response'] else None
        })

    except Exception as e:
        logger.error(
            f"Error in get_agent_response: {str(e)}",
            extra={
                'agent_id': agent_id,
                'conversation_id': conversation_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent/<int:agent_id>/receive/<int:interaction_id>', methods=['POST'])
def receive_message(agent_id, interaction_id):
    """Process a received message"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get message details
        cursor.execute("""
            SELECT id, sender_id, receiver_id, content, processed_message,
                   interaction_type, status, created_at
            FROM messages 
            WHERE id = %s AND receiver_id = %s
        """, (interaction_id, agent_id))
        
        message = cursor.fetchone()
        if not message:
            return jsonify({
                'status': 'error',
                'message': 'Message not found'
            }), 404
        
        # Convert datetime objects to strings for JSON serialization
        if message:
            if message.get('created_at'):
                if isinstance(message['created_at'], datetime):
                    message['created_at'] = message['created_at'].isoformat()
                else:
                    message['created_at'] = str(message['created_at'])
        
        # Update message status and processed content
        cursor.execute("""
            UPDATE messages 
            SET status = 'processed',
                processed_message = content
            WHERE id = %s
        """, (interaction_id,))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error receiving message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/workflow', methods=['POST'])
def start_agent_workflow(agent_id):
    """Start a multi-agent workflow"""
    try:
        workflow_data = request.json
        if not workflow_data:
            return jsonify({
                "status": "error",
                "message": "Workflow data is required"
            }), 400

        # Initialize source agent
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            return jsonify({"status": "error", "message": "Source agent not found"}), 404

        # Start workflow
        result = agent.start_workflow(workflow_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def initialize_agent_from_db(agent_id: int) -> Agent:
    """Helper function to initialize an agent from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get agent details including team_id
        cursor.execute("""
            SELECT a.*, ta.team_id 
            FROM agents a
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            WHERE a.id = %s
        """, (agent_id,))
        agent_data = cursor.fetchone()
        
        if not agent_data:
            logger.error(f"Agent {agent_id} not found in database")
            return None

        # Create agent instance
        agent = Agent(
            agent_data["id"],
            agent_data["name"],
            agent_data["memory_type"],
            agent_data["foundation_model"],
            agent_data.get("team_id")  # Now getting team_id from join
        )

        # Load agent's memories
        try:
            agent.load_memories(cursor)
            logger.info(f"Loaded memories for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error loading memories for agent {agent_id}: {e}", exc_info=True)

        # Get agent's tools
        try:
            cursor.execute("""
                SELECT t.* 
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = %s
            """, (agent_id,))
            
            tools_data = cursor.fetchall()
            logger.info(f"Found {len(tools_data)} tools for agent {agent_id}")
            
            for tool_data in tools_data:
                try:
                    tool = create_tool(tool_data)
                    agent.add_tool(tool)
                    logger.info(f"Added tool {tool_data['tool_name']} to agent {agent_id}")
                except ValueError as e:
                    logger.error(f"Failed to create tool for agent {agent_id}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error creating tool for agent {agent_id}: {e}", exc_info=True)

            if not agent.tools:
                logger.warning(f"No tools were successfully loaded for agent {agent_id}")
                
        except Exception as e:
            logger.error(f"Error loading tools for agent {agent_id}: {e}", exc_info=True)

        return agent

    except Exception as e:
        logger.error(f"Error initializing agent {agent_id}: {e}", exc_info=True)
        return None
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Error handlers with logging
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(
        f"404 Not Found: {request.url}",
        extra={'path': request.path, 'method': request.method}
    )
    return jsonify({"status": "error", "message": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(
        f"500 Internal Server Error: {str(error)}",
        extra={
            'path': request.path,
            'method': request.method,
            'error': str(error),
            'traceback': traceback.format_exc()
        }
    )
    return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/ml/tools', methods=['GET'])
def get_tools():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, tool_name, description, type FROM tools")
        tools = cursor.fetchall()
        
        return jsonify({
            'status': 'success',
            'tools': tools
        })
        
    except Exception as e:
        logger.error(f"Error fetching tools: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/tools/<int:tool_id>', methods=['GET', 'PUT'])
def manage_tool(tool_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute(
                "SELECT id, tool_name, description, type FROM tools WHERE id = %s",
                (tool_id,)
            )
            tool = cursor.fetchone()
            
            if not tool:
                return jsonify({
                    'status': 'error',
                    'message': 'Tool not found'
                }), 404
                
            return jsonify({
                'status': 'success',
                'tool': tool
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            cursor.execute(
                """UPDATE tools 
                SET tool_name = %s, description = %s, type = %s 
                WHERE id = %s""",
                (data['tool_name'], data['description'], data['type'], tool_id)
            )
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Tool updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error managing tool {tool_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/tools', methods=['GET', 'POST'])
def manage_agent_tools(agent_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT t.id, t.tool_name, t.description, t.type
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = %s
            """, (agent_id,))
            tools = cursor.fetchall()
            
            return jsonify({
                'status': 'success',
                'tools': tools
            })
            
        elif request.method == 'POST':
            data = request.get_json()
            tool_ids = data.get('tool_ids', [])
            
            # First remove existing tools
            cursor.execute(
                "DELETE FROM agent_tools WHERE agent_id = %s",
                (agent_id,)
            )
            
            # Add new tools
            for tool_id in tool_ids:
                cursor.execute(
                    """INSERT INTO agent_tools (agent_id, tool_id)
                    VALUES (%s, %s)""",
                    (agent_id, tool_id)
                )
                
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Agent tools updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error managing tools for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/tool/<int:tool_id>', methods=['POST', 'DELETE'])
def manage_single_agent_tool(agent_id, tool_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            cursor.execute(
                """INSERT INTO agent_tools (agent_id, tool_id)
                VALUES (%s, %s)""",
                (agent_id, tool_id)
            )
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Tool added to agent successfully'
            })
            
        elif request.method == 'DELETE':
            cursor.execute(
                """DELETE FROM agent_tools 
                WHERE agent_id = %s AND tool_id = %s""",
                (agent_id, tool_id)
            )
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Tool removed from agent successfully'
            })
            
    except Exception as e:
        logger.error(f"Error managing tool {tool_id} for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/execute_all', methods=['POST'])
@log_execution
def execute_all_tools(agent_id):
    """Execute a command with all tools available to the agent"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Command is required'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Initialize agent
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            return jsonify({
                'status': 'error',
                'message': 'Agent not found'
            }), 404

        # Set correlation ID for tracking
        agent.set_correlation_id(str(uuid.uuid4()))

        # Execute command with all tools
        result = agent.execute_with_tools(data['command'])
        
        # Convert any non-serializable objects to strings
        def serialize_value(value):
            if isinstance(value, (datetime, decimal.Decimal)):
                return str(value)
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            return value

        # Clean the result for JSON serialization
        serializable_result = serialize_value(result)
        
        if result.get('status') == 'error':
            return jsonify(serializable_result), 500

        return jsonify(serializable_result)

    except Exception as e:
        logger.error(
            f"Error executing command with all tools: {str(e)}",
            extra={
                'agent_id': agent_id,
                'error_msg': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass

@app.route('/api/ml/agent-memory', methods=['POST'])
@log_execution
def create_agent_memory():
    """Create a new memory for an agent"""
    try:
        data = request.json
        required_fields = ['agent_id', 'memory_type']
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing required fields in request: {data}")
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Verify agent exists
            cursor.execute("SELECT id FROM agents WHERE id = %s", (data['agent_id'],))
            if not cursor.fetchone():
                logger.warning(f"Agent {data['agent_id']} not found")
                return jsonify({
                    "status": "error",
                    "message": f"Agent with id {data['agent_id']} not found"
                }), 404

            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    agent_id INT NOT NULL,
                    memory_type VARCHAR(50) NOT NULL,
                    start_prompt TEXT,
                    end_prompt TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents(id)
                )
            """)

            # Insert memory
            insert_query = """
                INSERT INTO agent_memory 
                (agent_id, memory_type, start_prompt, end_prompt, context)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                data['agent_id'],
                data['memory_type'],
                data.get('start_prompt'),
                data.get('end_prompt'),
                data.get('context')
            ))
            conn.commit()
            memory_id = cursor.lastrowid

            # Fetch the created memory
            cursor.execute("SELECT * FROM agent_memory WHERE id = %s", (memory_id,))
            memory = cursor.fetchone()

            logger.info(f"Created memory for agent {data['agent_id']}: {memory}")
            return jsonify({
                "status": "success",
                "memory": memory
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Error creating agent memory: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to create memory: {str(e)}"
        }), 500

@app.route('/api/tools/<int:tool_id>', methods=['GET'])
def get_tool(tool_id):
    """Get details of a specific tool"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, tool_name, description, type, hostname, auth_method
            FROM tools 
            WHERE id = %s
        """, (tool_id,))
        
        tool = cursor.fetchone()
        
        if not tool:
            return jsonify({
                'status': 'error',
                'message': 'Tool not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'tool_name': tool['tool_name'],
            'tool_type': tool['type'],
            'hostname': tool['hostname'],
            'auth_method': tool['auth_method']
        })
        
    except Exception as e:
        logger.error(f"Error fetching tool {tool_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Initialize database tables
def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                conversation_id VARCHAR(255) UNIQUE NOT NULL,
                content JSON,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_conversation_id (conversation_id)
            )
        """)

        # Create agents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                memory_type VARCHAR(50) NOT NULL,
                foundation_model VARCHAR(50) NOT NULL,
                status VARCHAR(20) DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        # Create team_messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                team_id VARCHAR(36) NOT NULL,
                task_id VARCHAR(36) NOT NULL,
                task_description TEXT NOT NULL,
                task_requirements JSON,
                team_config JSON,
                status VARCHAR(20) DEFAULT 'pending',
                result JSON,
                error_message TEXT,
                processing_time INT,
                agent_responses JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_team_id (team_id),
                INDEX idx_task_id (task_id),
                INDEX idx_status (status)
            )
        """)
        
        # Create agent_memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_memory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_id INT NOT NULL,
                memory_type VARCHAR(50) NOT NULL,
                start_prompt TEXT,
                end_prompt TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id)
            )
        """)
        
        # Drop and recreate messages table to update schema
        cursor.execute("DROP TABLE IF EXISTS messages")
        cursor.execute("""
            CREATE TABLE messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT NULL,  -- Allow NULL for system/user messages
                receiver_id INT NOT NULL,
                content TEXT NOT NULL,
                processed_message TEXT,
                model_response TEXT,
                interaction_type VARCHAR(50) DEFAULT 'direct',
                conversation_id VARCHAR(36),
                team_id INT,
                status VARCHAR(20) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (receiver_id) REFERENCES agents(id),
                FOREIGN KEY (sender_id) REFERENCES agents(id)
            )
        """)

        # Create tools table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tools (
                id INT AUTO_INCREMENT PRIMARY KEY,
                tool_name VARCHAR(255) NOT NULL,
                description TEXT,
                type VARCHAR(50) NOT NULL,
                hostname VARCHAR(255),
                username VARCHAR(255),
                password VARCHAR(255),
                auth_method VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)

        # Create agent_tools table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_tools (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_id INT NOT NULL,
                tool_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES agents(id),
                FOREIGN KEY (tool_id) REFERENCES tools(id)
            )
        """)
        
        # Check if test agent exists
        cursor.execute("SELECT id FROM agents WHERE id = 10")
        if not cursor.fetchone():
            # Create test agent
            cursor.execute("""
                INSERT INTO agents (id, name, memory_type, foundation_model, status)
                VALUES (10, 'Databricks Agent', 'SHORT_TERM_MEMORY', 'gpt-4', 'active')
            """)
            logger.info("Created test agent with ID 10")

        # Check if test tool exists
        cursor.execute("SELECT id FROM tools WHERE id = 5")
        if not cursor.fetchone():
            # Create test tool
            cursor.execute("""
                INSERT INTO tools (id, tool_name, description, type, hostname, auth_method)
                VALUES (5, 'DBX Tool', 'Databricks Integration Tool', 'WebService', 'databricks.example.com', 'token')
            """)
            logger.info("Created test tool with ID 5")

            # Associate tool with agent
            cursor.execute("""
                INSERT IGNORE INTO agent_tools (agent_id, tool_id)
                VALUES (10, 5)
            """)
            logger.info("Associated tool 5 with agent 10")
        
        conn.commit()
        logger.info("Database tables initialized successfully")
        
    except mysql.connector.Error as e:
        logger.error(f"Database error during initialization: {e}", exc_info=True)
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Initialize database on startup
init_db()

@app.route('/api/debug/db-contents', methods=['GET'])
def get_db_contents():
    """Debug endpoint to check database contents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        tables = ['agents', 'agent_memory', 'messages', 'tools', 'agent_tools']
        contents = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                contents[table] = cursor.fetchall()
                # Convert datetime objects to strings for JSON serialization
                if contents[table]:
                    for row in contents[table]:
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()
                logger.info(f"Found {len(contents[table])} rows in {table}")
            except Exception as e:
                logger.error(f"Error fetching from {table}: {str(e)}")
                contents[table] = {"error": str(e)}
        
        return jsonify({
            "status": "success",
            "database_contents": contents
        })
        
    except Exception as e:
        logger.error(f"Error checking database contents: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/debug/db-connection', methods=['GET'])
def check_db_connection():
    """Debug endpoint to verify database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try a simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Get database version
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        # Get table counts
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_ROWS
            FROM information_schema.tables
            WHERE TABLE_SCHEMA = %s
        """, (db_config['database'],))
        table_counts = cursor.fetchall()
        
        return jsonify({
            "status": "success",
            "connection": "active",
            "database": db_config['database'],
            "version": version[0] if version else None,
            "table_counts": dict(table_counts)
        })
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/team/execute', methods=['POST'])
@log_execution
def execute_team_task():
    """Execute a task using a team of agents"""
    conn = None
    cursor = None
    start_time = datetime.now()
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        # Validate required fields
        required_fields = ['team_config', 'task']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        # Create team instance
        team = Team(
            team_id=str(uuid.uuid4()),
            name=data['team_config'].get('name', 'Task Team'),
            description=data['team_config'].get('description', 'Team for task execution')
        )

        # Add team members
        for member_config in data['team_config'].get('members', []):
            member = TeamMember(
                agent_id=member_config['agent_id'],
                priority=member_config.get('priority', 1),
                accuracy_threshold=member_config.get('accuracy_threshold', 0.8),
                success_rate=member_config.get('success_rate', 0.9)
            )
            team.add_member(member)

        if not team.members:
            return jsonify({
                "status": "error",
                "message": "No team members specified"
            }), 400

        # Create task
        task = TeamTask(
            task_id=str(uuid.uuid4()),
            description=data['task'].get('description', ''),
            requirements=data['task'].get('requirements', {})
        )
        team.assign_task(task)

        # Store initial task record
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            insert_query = """
                INSERT INTO team_messages (
                    team_id, task_id, task_description, task_requirements, 
                    team_config, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(insert_query, (
                team.team_id,
                task.task_id,
                task.description,
                json.dumps(task.requirements),
                json.dumps(data['team_config']),
                'processing'
            ))
            
            conn.commit()
            logger.info(f"Stored initial team task record for task {task.task_id}")
            
        except Exception as db_error:
            logger.error(f"Database error storing team task: {str(db_error)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            safe_close_connection(conn, cursor)

        # Execute task with team
        final_result = execute_task_with_team(team, task)
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds())

        # Update task record with results
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            update_query = """
                UPDATE team_messages 
                SET status = %s,
                    result = %s,
                    processing_time = %s,
                    agent_responses = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE team_id = %s AND task_id = %s
            """
            
            cursor.execute(update_query, (
                final_result.get('final_status', 'failed'),
                json.dumps(final_result),
                processing_time,
                json.dumps(final_result.get('conversation_context', [])),
                team.team_id,
                task.task_id
            ))
            
            conn.commit()
            logger.info(f"Updated team task record with results for task {task.task_id}")
            
        except Exception as db_error:
            logger.error(f"Database error updating team task results: {str(db_error)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            safe_close_connection(conn, cursor)

        return jsonify({
            "status": "success",
            "team": team.to_dict(),
            "result": final_result,
            "processing_time_seconds": processing_time
        })

    except Exception as e:
        logger.error(f"Error executing team task: {str(e)}", exc_info=True)
        
        # Store error in database if we have team/task IDs
        if 'team' in locals() and 'task' in locals():
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                update_query = """
                    UPDATE team_messages 
                    SET status = 'failed',
                        error_message = %s,
                        processing_time = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE team_id = %s AND task_id = %s
                """
                
                processing_time = int((datetime.now() - start_time).total_seconds())
                
                cursor.execute(update_query, (
                    str(e),
                    processing_time,
                    team.team_id,
                    task.task_id
                ))
                
                conn.commit()
                
            except Exception as db_error:
                logger.error(f"Database error storing team task error: {str(db_error)}", exc_info=True)
            finally:
                safe_close_connection(conn, cursor)
        
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc()
        }), 500

@app.route('/api/ml/team/history', methods=['GET'])
def get_team_history():
    """Get history of team messages and tasks"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get optional query parameters
        team_id = request.args.get('team_id')
        status = request.args.get('status')
        limit = request.args.get('limit', 100)
        
        # Build query
        query = "SELECT * FROM team_messages WHERE 1=1"
        params = []
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
            
        if status:
            query += " AND status = %s"
            params.append(status)
            
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(int(limit))
        
        # Execute query
        cursor.execute(query, tuple(params))
        history = cursor.fetchall()
        
        # Convert datetime objects to strings
        for record in history:
            record['created_at'] = record['created_at'].isoformat() if record['created_at'] else None
            record['updated_at'] = record['updated_at'].isoformat() if record['updated_at'] else None
        
        return jsonify({
            "status": "success",
            "history": history
        })
        
    except Exception as e:
        logger.error(f"Error fetching team history: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        safe_close_connection(conn, cursor)

def execute_task_with_team(team: Team, task: TeamTask) -> Dict[str, Any]:
    """Execute a task using a team of agents with proper coordination"""
    try:
        logger.info(f"Starting team execution for task {task.task_id}")
        final_results = []
        
        # Track conversation context
        conversation_context = []
        
        # Execute task with each team member in priority order
        for member in team.members:
            try:
                # Initialize agent
                agent = initialize_agent_from_db(member.agent_id)
                if not agent:
                    logger.error(f"Could not initialize agent {member.agent_id}")
                    continue

                # Set correlation ID for tracking
                agent.set_correlation_id(task.task_id)

                # Prepare message with context and requirements
                message = {
                    "task_description": task.description,
                    "requirements": task.requirements,
                    "conversation_context": conversation_context,
                    "accuracy_threshold": member.accuracy_threshold,
                    "success_rate": member.success_rate
                }

                # Execute with agent
                result = agent.execute_with_tools(json.dumps(message))
                
                if result.get('status') == 'success':
                    # Format code blocks in response if present
                    response_text = result.get('llm_response', '')
                    if any(lang in response_text.lower() for lang in ['python', 'java', 'javascript', 'typescript', 'bash', 'sql']):
                        # Extract and format code blocks
                        formatted_response = []
                        lines = response_text.split('\n')
                        in_code_block = False
                        current_block = []
                        current_language = ''
                        
                        for line in lines:
                            if line.startswith('```'):
                                if in_code_block:
                                    # End code block
                                    formatted_response.append(f"```{current_language}\n{''.join(current_block)}\n```")
                                    current_block = []
                                    in_code_block = False
                                else:
                                    # Start code block
                                    in_code_block = True
                                    current_language = line[3:].strip()
                            elif in_code_block:
                                current_block.append(line + '\n')
                            else:
                                formatted_response.append(line)
                        
                        response_text = '\n'.join(formatted_response)
                    
                    # Add to conversation context
                    conversation_context.append({
                        "agent_id": member.agent_id,
                        "response": response_text
                    })
                    
                    # Add to results
                    final_results.append({
                        "agent_id": member.agent_id,
                        "priority": member.priority,
                        "result": result
                    })

                    # Update task status
                    task.status = "in_progress"
                    task.results.append(result)

            except Exception as agent_error:
                logger.error(f"Error with agent {member.agent_id}: {str(agent_error)}", exc_info=True)
                continue

        # Aggregate results
        aggregated_result = {
            "status": "success",
            "task_id": task.task_id,
            "team_id": team.team_id,
            "results": final_results,
            "conversation_context": conversation_context,
            "final_status": "completed" if final_results else "failed"
        }

        # Update task status
        task.status = aggregated_result["final_status"]
        task.updated_at = datetime.now()

        return aggregated_result

    except Exception as e:
        logger.error(f"Error in team execution: {str(e)}", exc_info=True)
        task.status = "failed"
        task.updated_at = datetime.now()
        return {
            "status": "error",
            "message": str(e),
            "task_id": task.task_id,
            "team_id": team.team_id
        }

@app.route('/api/ml/conversation/store', methods=['POST'])
@log_execution
def store_conversation():
    """Store conversation history in the database"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['conversation_id', 'content', 'metadata']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Missing required fields. Required: {required_fields}'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Store the conversation
            insert_query = """
                INSERT INTO conversations (
                    conversation_id,
                    content,
                    metadata,
                    created_at
                ) VALUES (%s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                    content = VALUES(content),
                    metadata = VALUES(metadata),
                    updated_at = NOW()
            """
            
            cursor.execute(insert_query, (
                data['conversation_id'],
                json.dumps(data['content']),
                json.dumps(data['metadata'])
            ))
            
            conn.commit()

            logger.info(f"Stored conversation {data['conversation_id']}")
            return jsonify({
                'status': 'success',
                'message': 'Conversation stored successfully',
                'conversation_id': data['conversation_id']
            })

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to store conversation: {str(e)}'
        }), 500

@app.route('/api/agent-interactions', methods=['GET'])
def get_agent_interactions():
    """Get agent interactions from messages table"""
    try:
        team_id = request.args.get('team_id')
        source = request.args.get('source')
        target = request.args.get('target')
        conversation_id = request.args.get('conversation_id')
        
        logger.info(f"[get_agent_interactions] Request params: team_id={team_id}, source={source}, target={target}, conversation_id={conversation_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query joining with agents table to get names
        query = """
            SELECT DISTINCT
                m.id,
                m.conversation_id,
                COALESCE(sa.name, 'OpenAI') as source_agent,
                COALESCE(ra.name, 'OpenAI') as target_agent,
                m.interaction_type,
                m.status,
                m.created_at as timestamp,
                m.content,
                m.processed_message,
                m.model_response
            FROM messages m
            LEFT JOIN agents sa ON m.sender_id = sa.id
            LEFT JOIN agents ra ON m.receiver_id = ra.id
            WHERE 1=1
        """
        params = []
        
        # Add filters
        if team_id:
            query += " AND m.team_id = %s"
            params.append(int(team_id))
        
        if source:
            query += " AND m.sender_id = %s"
            params.append(int(source))
            
        if target:
            query += " AND m.receiver_id = %s"
            params.append(int(target))
            
        if conversation_id:
            query += " AND m.conversation_id = %s"
            params.append(conversation_id)
            
        query += " ORDER BY m.created_at DESC"
        
        logger.info(f"[get_agent_interactions] Executing query: {query}")
        logger.info(f"[get_agent_interactions] Query params: {params}")
        
        cursor.execute(query, params)
        interactions = cursor.fetchall()
        logger.info(f"[get_agent_interactions] Found {len(interactions)} interactions")
        
        # Convert datetime objects to strings and ensure all fields are JSON serializable
        formatted_interactions = []
        for interaction in interactions:
            formatted_interaction = {}
            for key, value in interaction.items():
                if isinstance(value, datetime):
                    formatted_interaction[key] = value.isoformat()
                else:
                    formatted_interaction[key] = value
            formatted_interactions.append(formatted_interaction)
        
        logger.info(f"[get_agent_interactions] Returning {len(formatted_interactions)} formatted interactions")
        return jsonify(formatted_interactions)
        
    except Exception as e:
        logger.error(f"Error fetching agent interactions: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    app.run(port=5000, debug=True) 