from flask import Flask, request, jsonify
from abc import ABC, abstractmethod
import mysql.connector
from mysql.connector import pooling
import os
from datetime import datetime, timedelta
from openai import OpenAI
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

# Load environment variables
load_dotenv()

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'admin',
    'password': 'gUest@Sep2',
    'database': 'multi_agentic_system'
}

# Initialize OpenAI client
client = OpenAI()  # This will automatically use OPENAI_API_KEY from environment variables

# Create connection pool
connection_pool = mysql.connector.pooling.MySQLConnectionPool(**db_config)

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
            # Use OpenAI's chat completion
            response = client.chat.completions.create(
                model="gpt-4",  # Using gpt-4 as specified in the example
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return {
                "status": "success",
                "response": response.choices[0].message.content,
                "model_used": "gpt-4"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

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
            validation_response = client.chat.completions.create(
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
        if not self.tools:
            return {"status": "error", "message": "No tools configured for this agent"}

        # Get context from memories
        context = self.get_context_from_memories()
        end_prompt = None
        if self.memories and self.memories[0].get('end_prompt'):
            end_prompt = self.memories[0]['end_prompt']

        # Process command with LLM first
        messages = self.format_messages_for_llm(command, context)
        llm_response = self.process_with_llm(messages)
        
        if llm_response["status"] != "success":
            return llm_response

        # Execute command with all tools
        tool_responses = []
        for tool in self.tools:
            result = tool.execute(llm_response["response"])
            tool_responses.append(result)

        # Validate responses if end prompt exists
        validation_results = []
        if end_prompt:
            for response in tool_responses:
                validation_result = self.validate_response_with_llm(
                    str(response),  # Convert response to string for validation
                    end_prompt
                )
                validation_results.append(validation_result)

        # Compile final response
        final_response = {
            "status": "success",
            "context": context,
            "memory_type": self.memory_type,
            "llm_response": llm_response["response"],
            "model_used": llm_response["model_used"],
            "tool_responses": tool_responses,
            "validation_results": validation_results if end_prompt else None
        }

        return final_response

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
            conn = connection_pool.get_connection()
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
            conn = connection_pool.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get interaction details
            cursor.execute("""
                SELECT id, source_agent_id, target_agent_id, message, 
                       processed_message, created_at, updated_at
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
        
        conn = connection_pool.get_connection()
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
def send_message(agent_id):
    try:
        data = request.get_json()
        target_agent_id = data.get('target_agent_id')
        message = data.get('message')
        interaction_type = data.get('interaction_type', 'direct')
        
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        # Insert message with processed_message field
        cursor.execute(
            """INSERT INTO messages 
            (sender_id, receiver_id, content, processed_message, interaction_type)
            VALUES (%s, %s, %s, %s, %s)""",
            (agent_id, target_agent_id, message, message, interaction_type)
        )
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Message sent successfully'
        })
        
    except Exception as e:
        logger.error(f"Error sending message from agent {agent_id}: {str(e)}")
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
def start_workflow(agent_id):
    try:
        data = request.get_json()
        workflow_type = data.get('type')
        agents = data.get('agents', [])
        message = data.get('message')
        
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        # Create workflow with message field
        cursor.execute(
            """INSERT INTO workflows (initiator_id, type, message)
            VALUES (%s, %s, %s)""",
            (agent_id, workflow_type, message)
        )
        workflow_id = cursor.lastrowid
        
        # Create workflow steps
        for idx, agent_id in enumerate(agents):
            cursor.execute(
                """INSERT INTO workflow_steps (workflow_id, agent_id, step_order)
                VALUES (%s, %s, %s)""",
                (workflow_id, agent_id, idx + 1)
            )
            
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'workflow_id': workflow_id
        })
        
    except Exception as e:
        logger.error(f"Error starting workflow for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/team/<int:team_id>/metrics', methods=['GET'])
def get_metrics(team_id):
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get basic team metrics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT m.id) as interaction_count,
                COUNT(DISTINCT tp.tool_id) as tool_count,
                COALESCE(
                    COUNT(CASE WHEN m.status = 'processed' THEN 1 END) * 100.0 / 
                    NULLIF(COUNT(m.id), 0),
                    0
                ) as success_rate
            FROM teams t
            LEFT JOIN team_agents ta ON t.id = ta.team_id
            LEFT JOIN messages m ON m.sender_id = ta.agent_id OR m.receiver_id = ta.agent_id
            LEFT JOIN team_tool_permissions tp ON tp.team_id = t.id
            WHERE t.id = %s
            GROUP BY t.id
        """, (team_id,))
        
        metrics = cursor.fetchone()
        
        # Ensure we have valid metrics
        if not metrics:
            metrics = {
                'interaction_count': 0,
                'tool_count': 0,
                'success_rate': 0.0
            }
        else:
            # Convert decimal values to float for JSON serialization
            metrics = {
                k: float(v) if isinstance(v, decimal.Decimal) else (
                    int(v) if isinstance(v, (int, float)) else v
                ) for k, v in metrics.items()
            }
        
        return jsonify({
            'status': 'success',
            'metrics': metrics,
            'time_range': request.args.get('time_range', '24h')
        })
        
    except Exception as e:
        logger.error(f"Error getting team metrics: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/team/<int:team_id>/config', methods=['GET', 'PUT'])
def team_config(team_id):
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True, buffered=True)  # Use buffered cursor
        
        if request.method == 'GET':
            # First check if team exists
            cursor.execute("SELECT id, name FROM teams WHERE id = %s", (team_id,))
            team = cursor.fetchone()
            
            if not team:
                return jsonify({
                    'status': 'error',
                    'message': 'Team not found'
                }), 404
            
            # Get team configuration
            cursor.execute("""
                SELECT config_data 
                FROM team_configurations
                WHERE team_id = %s
            """, (team_id,))
            
            config = cursor.fetchone() or {}  # Ensure we consume the result
            config_data = {}
            
            if config:
                try:
                    if isinstance(config.get('config_data'), str):
                        config_data = json.loads(config['config_data'])
                    elif isinstance(config.get('config_data'), dict):
                        config_data = config['config_data']
                    elif config.get('config_data') is None:
                        config_data = {}
                except (json.JSONDecodeError, TypeError, KeyError):
                    config_data = {}
            
            # Get permissions
            cursor.execute("""
                SELECT tool_id, permission_level
                FROM team_tool_permissions
                WHERE team_id = %s
            """, (team_id,))
            
            # Convert MySQL results to plain dictionaries and ensure we consume all results
            permissions = []
            rows = cursor.fetchall() or []  # Ensure we consume all results
            for row in rows:
                perm = {}
                for key, value in row.items():
                    if isinstance(value, (datetime, decimal.Decimal)):
                        perm[key] = str(value)
                    else:
                        perm[key] = value
                permissions.append(perm)
            
            # Convert team data to plain dictionary
            team_dict = {}
            for key, value in team.items():
                if isinstance(value, (datetime, decimal.Decimal)):
                    team_dict[key] = str(value)
                else:
                    team_dict[key] = value
            
            response = {
                'status': 'success',
                'config': {
                    'team_id': team_dict['id'],
                    'name': team_dict['name'],
                    'settings': config_data,
                    'permissions': permissions
                }
            }
            
            return jsonify(response)
            
        elif request.method == 'PUT':
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No data provided'
                }), 400
                
            config = data.get('config', {})
            permissions = data.get('permissions', [])
            
            # First check if team exists
            cursor.execute("SELECT id FROM teams WHERE id = %s", (team_id,))
            if not cursor.fetchone():  # Ensure we consume the result
                return jsonify({
                    'status': 'error',
                    'message': 'Team not found'
                }), 404
            
            try:
                # Update team configuration using config_data field
                cursor.execute(
                    """INSERT INTO team_configurations (team_id, config_data)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE config_data = VALUES(config_data)""",
                    (team_id, json.dumps(config))
                )
                
                # Update tool permissions
                if permissions:
                    # First remove existing permissions
                    cursor.execute(
                        "DELETE FROM team_tool_permissions WHERE team_id = %s",
                        (team_id,)
                    )
                    
                    # Add new permissions
                    for perm in permissions:
                        cursor.execute(
                            """INSERT INTO team_tool_permissions 
                            (team_id, tool_id, permission_level)
                            VALUES (%s, %s, %s)""",
                            (team_id, perm['tool_id'], perm['level'])
                        )
                
                conn.commit()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Configuration updated successfully'
                })
                
            except Exception as e:
                if conn:
                    conn.rollback()
                logger.error(f"Database error updating team config: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f'Database error: {str(e)}'
                }), 500
            
    except Exception as e:
        logger.error(f"Error managing team {team_id} configuration: {str(e)}")
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

# Agent Memory CRUD Endpoints

@app.route('/api/ml/agent-memory', methods=['POST'])
def create_agent_memory():
    try:
        data = request.json
        required_fields = ['agent_id', 'memory_type']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify agent exists
        cursor.execute("SELECT id FROM agents WHERE id = %s", (data['agent_id'],))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "status": "error",
                "message": f"Agent with id {data['agent_id']} not found"
            }), 404

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

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "memory": memory
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent-memory/<int:memory_id>', methods=['GET'])
def get_agent_memory(memory_id):
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM agent_memory WHERE id = %s", (memory_id,))
        memory = cursor.fetchone()

        cursor.close()
        conn.close()

        if not memory:
            return jsonify({
                "status": "error",
                "message": f"Memory with id {memory_id} not found"
            }), 404

        return jsonify({
            "status": "success",
            "memory": memory
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent/<int:agent_id>/memories', methods=['GET'])
def get_agent_memories(agent_id):
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify agent exists
        cursor.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "status": "error",
                "message": f"Agent with id {agent_id} not found"
            }), 404

        # Get all memories for the agent
        cursor.execute("SELECT * FROM agent_memory WHERE agent_id = %s ORDER BY created_at DESC", (agent_id,))
        memories = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "memories": memories
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent-memory/<int:memory_id>', methods=['PUT'])
def update_agent_memory(memory_id):
    try:
        data = request.json
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if memory exists
        cursor.execute("SELECT * FROM agent_memory WHERE id = %s", (memory_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "status": "error",
                "message": f"Memory with id {memory_id} not found"
            }), 404

        # Update memory
        update_query = """
            UPDATE agent_memory 
            SET memory_type = %s,
                start_prompt = %s,
                end_prompt = %s,
                context = %s
            WHERE id = %s
        """
        cursor.execute(update_query, (
            data.get('memory_type'),
            data.get('start_prompt'),
            data.get('end_prompt'),
            data.get('context'),
            memory_id
        ))
        conn.commit()

        # Fetch updated memory
        cursor.execute("SELECT * FROM agent_memory WHERE id = %s", (memory_id,))
        updated_memory = cursor.fetchone()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "memory": updated_memory
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent-memory/<int:memory_id>', methods=['DELETE'])
def delete_agent_memory(memory_id):
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if memory exists
        cursor.execute("SELECT * FROM agent_memory WHERE id = %s", (memory_id,))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({
                "status": "error",
                "message": f"Memory with id {memory_id} not found"
            }), 404

        # Delete memory
        cursor.execute("DELETE FROM agent_memory WHERE id = %s", (memory_id,))
        conn.commit()

        cursor.close()
        conn.close()

        return jsonify({
            "status": "success",
            "message": f"Memory with id {memory_id} deleted successfully"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# New API endpoints for agent interactions

@app.route('/api/ml/agent/<int:agent_id>/send', methods=['POST'])
@log_execution
def send_agent_message(agent_id):
    """Send a message from one agent to another"""
    try:
        data = request.json
        target_agent_id = data.get('target_agent_id')
        message = data.get('message')
        interaction_type = data.get('interaction_type', InteractionType.DIRECT.value)

        if not all([target_agent_id, message]):
            logger.warning(
                "Invalid request parameters",
                extra={
                    'agent_id': agent_id,
                    'target_agent_id': target_agent_id,
                    'message_provided': bool(message)
                }
            )
            return jsonify({
                "status": "error",
                "message": "target_agent_id and message are required"
            }), 400

        # Initialize source agent
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found")
            return jsonify({"status": "error", "message": "Source agent not found"}), 404

        # Set correlation ID for tracking
        agent.set_correlation_id(str(uuid.uuid4()))

        # Send message
        result = agent.send_message(target_agent_id, message, interaction_type)
        return jsonify(result)

    except Exception as e:
        logger.error(
            f"Error in send_agent_message: {str(e)}",
            extra={
                'agent_id': agent_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent/<int:agent_id>/receive/<int:interaction_id>', methods=['POST'])
def receive_message(agent_id, interaction_id):
    """Process a received message"""
    try:
        conn = connection_pool.get_connection()
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
        conn = connection_pool.get_connection()
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
        agent.load_memories(cursor)

        # Get agent's tools
        cursor.execute("""
            SELECT t.* 
            FROM tools t
            JOIN agent_tools at ON t.id = at.tool_id
            WHERE at.agent_id = %s
        """, (agent_id,))
        
        tools_data = cursor.fetchall()
        for tool_data in tools_data:
            try:
                tool = create_tool(tool_data)
                agent.add_tool(tool)
            except ValueError as e:
                print(f"Warning: Failed to create tool: {e}")

        cursor.close()
        conn.close()

        return agent

    except Exception as e:
        print(f"Error initializing agent: {e}")
        return None

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
        conn = connection_pool.get_connection()
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
        conn = connection_pool.get_connection()
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
        conn = connection_pool.get_connection()
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
        conn = connection_pool.get_connection()
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

        conn = connection_pool.get_connection()
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

if __name__ == '__main__':
    app.run(port=5000, debug=True) 