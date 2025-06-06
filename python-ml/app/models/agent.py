from typing import Dict, Any, List, Optional, NamedTuple
from datetime import datetime
from app.utils.enums import AgentStatus
from app.utils.logger import logger
from app.config.openai_config import get_openai_client
from app.core.tools import Tool, GitHubTool
import json
import re

class AgentTool(NamedTuple):
    """Data structure for agent tools"""
    name: str
    description: Optional[str]
    type: str

class Agent:
    """Data model for an agent"""
    
    def __init__(
        self,
        agent_id: int,
        name: str,
        memory_type: str,
        foundation_model: str,
        team_id: Optional[int] = None,
        status: str = AgentStatus.IDLE.value,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.agent_id = agent_id
        self.name = name
        self.memory_type = memory_type
        self.foundation_model = foundation_model
        self.team_id = team_id
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.tools: List[AgentTool] = []  # List of AgentTool objects
        self.metrics: Dict[str, Any] = {
            'total_interactions': 0,
            'successful_interactions': 0,
            'failed_interactions': 0,
            'average_response_time': 0.0
        }
        self._openai = None  # Lazy-loaded OpenAI client
        self.correlation_id = None  # For tracking agent actions

    def get_openai_client(self):
        """Get or initialize OpenAI client"""
        if self._openai is None:
            self._openai = get_openai_client()
        return self._openai

    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'memory_type': self.memory_type,
            'foundation_model': self.foundation_model,
            'team_id': self.team_id,
            'status': self.status,
            'tools': [{'name': t.name, 'description': t.description, 'type': t.type} for t in self.tools],
            'metrics': self.metrics,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agent':
        """Create an agent instance from dictionary data"""
        try:
            agent = cls(
                agent_id=data['agent_id'],
                name=data['name'],
                memory_type=data['memory_type'],
                foundation_model=data['foundation_model'],
                team_id=data.get('team_id'),
                status=data.get('status', AgentStatus.IDLE.value),
                created_at=datetime.fromisoformat(data['created_at']) if 'created_at' in data else None,
                updated_at=datetime.fromisoformat(data['updated_at']) if 'updated_at' in data else None
            )
            # Convert tool dictionaries to AgentTool objects
            for tool_data in data.get('tools', []):
                agent.add_tool(tool_data['name'], tool_data['description'], tool_data['type'])
            agent.metrics = data.get('metrics', {})
            return agent
        except Exception as e:
            logger.error(f"Error creating agent from dictionary: {str(e)}")
            raise ValueError(f"Invalid agent data: {str(e)}")

    def update_metrics(self, interaction_success: bool, response_time: float) -> None:
        """Update agent metrics after an interaction"""
        self.metrics['total_interactions'] += 1
        if interaction_success:
            self.metrics['successful_interactions'] += 1
        else:
            self.metrics['failed_interactions'] += 1
        
        # Update average response time
        current_avg = self.metrics['average_response_time']
        total_interactions = self.metrics['total_interactions']
        self.metrics['average_response_time'] = (
            (current_avg * (total_interactions - 1) + response_time) / total_interactions
        )
        
        self.updated_at = datetime.utcnow()

    def add_tool(self, name: str, description: Optional[str], tool_type: str) -> None:
        """Add a tool to the agent"""
        tool = AgentTool(name=name, description=description, type=tool_type)
        self.tools.append(tool)
        logger.info(f"Tool {name} added to agent {self.agent_id}")

    def remove_tool(self, name: str) -> None:
        """Remove a tool from the agent by name"""
        self.tools = [t for t in self.tools if t.name != name]
        self.updated_at = datetime.utcnow()
        logger.info(f"Tool {name} removed from agent {self.agent_id}")

    def update_status(self, status: str) -> None:
        """Update agent status"""
        self.status = status
        self.updated_at = datetime.utcnow()
        logger.info(f"Agent {self.agent_id} status updated to {status}")

    def get_success_rate(self) -> float:
        """Calculate the agent's success rate"""
        total = self.metrics['total_interactions']
        if total == 0:
            return 0.0
        return self.metrics['successful_interactions'] / total * 100 

    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for tracking agent actions"""
        self.correlation_id = correlation_id
        logger.info(f"Set correlation ID for agent {self.agent_id}: {correlation_id}")

    def execute_with_tools(self, message: str) -> Dict[str, Any]:
        """Execute a task using the agent's tools"""
        try:
            # Get OpenAI client
            openai = self.get_openai_client()
            
            # Parse the message
            try:
                message_data = json.loads(message)
                task_description = message_data.get('task_description', '')
                requirements = message_data.get('requirements', {})
            except json.JSONDecodeError:
                task_description = message
                requirements = {}
            
            # Add task description to requirements
            requirements['task_description'] = task_description
            
            logger.info(f"[AGENT EXECUTION] Processing task: {task_description}")
            logger.debug(f"[AGENT EXECUTION] Requirements: {json.dumps(requirements, indent=2)}")
            
            # Prepare system message based on agent's role and tools
            tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in self.tools])
            system_message = f"""You are {self.name}, an AI agent with the following tools:
{tools_desc}

IMPORTANT: When users mention any dataset (like "nfl favorite team", "nfl data", etc.), you MUST:
1. ALWAYS use the GitHub Tool to fetch the actual dataset
2. DO NOT treat it as a conversational question
3. DO NOT ask for clarification unless the dataset name is completely unclear
4. DO NOT say you're an AI or talk about preferences
5. Instead, immediately use the GitHub Tool to get the data

For example:
- If user asks "nfl favorite team" -> Use GitHub Tool to get the NFL favorite team dataset
- If user asks "show me nfl data" -> Use GitHub Tool to get the NFL dataset
- If user asks about any sports team data -> Use GitHub Tool to find relevant datasets

For other types of queries:
- Only use tools when they are actually needed for the task
- For simple queries like greetings or general questions, do not use any tools

Task Requirements:
{json.dumps(requirements, indent=2)}
"""
            
            logger.debug("[AGENT EXECUTION] Calling OpenAI for task analysis")
            # Call OpenAI API for task analysis
            response = openai.ChatCompletion.create(
                model=self.foundation_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": task_description}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Extract initial LLM response
            initial_llm_response = response.choices[0].message.content
            logger.info("[AGENT EXECUTION] Received initial analysis from LLM")
            logger.debug(f"[AGENT EXECUTION] Initial analysis: {initial_llm_response}")
            
            # Check if the response indicates any tools are needed
            # Improved tool detection logic
            tools_needed = False
            tools_to_use = []
            
            for tool in self.tools:
                # Check for exact tool name match
                if tool.name.lower() in initial_llm_response.lower():
                    tools_needed = True
                    tools_to_use.append(tool)
                    continue
                
                # Check for task-specific keywords
                if tool.type.lower() == 'github':
                    github_keywords = ['github', 'dataset', 'data', 'csv', 'repository', 'repo']
                    if any(keyword in task_description.lower() for keyword in github_keywords):
                        tools_needed = True
                        tools_to_use.append(tool)
                        logger.info(f"[AGENT EXECUTION] Detected need for GitHub tool based on keywords in task")
                elif tool.type.lower() == 'database':
                    db_keywords = ['database', 'sql', 'query', 'table', 'record']
                    if any(keyword in task_description.lower() for keyword in db_keywords):
                        tools_needed = True
                        tools_to_use.append(tool)
                        logger.info(f"[AGENT EXECUTION] Detected need for Database tool based on keywords in task")
            
            logger.info(f"[AGENT EXECUTION] Tools needed: {tools_needed}")
            if tools_needed:
                logger.info(f"[AGENT EXECUTION] Tools to use: {[t.name for t in tools_to_use]}")
            
            # Initialize results
            tool_results = []
            aggregated_data = {
                'successful_tools': 0,
                'failed_tools': 0,
                'data_points': [],
                'errors': []
            }

            # Only execute tools if they are needed
            if tools_needed:
                for tool in tools_to_use:
                    try:
                        logger.info(f"[AGENT EXECUTION] Executing tool: {tool.name}")
                        # Execute tool based on its type
                        tool_result = self._execute_tool(tool, task_description, requirements)
                        
                        # Format tool result
                        formatted_result = {
                            "tool_name": tool.name,
                            "status": tool_result.get('status', 'failed'),
                            "result": {
                                "tool_id": tool_result.get('tool_id'),
                                "tool_name": tool.name,
                                "tool_type": tool.type,
                                "hostname": tool_result.get('hostname', ''),
                                "auth_method": tool_result.get('auth_method', 'None'),
                                "command": tool_result.get('command', ''),
                                "status": tool_result.get('status', 'failed'),
                                "message": tool_result.get('message', f"Agent has used the {tool.name} ({tool.type})"),
                                # Tool-specific data
                                **tool_result.get('data', {})
                            }
                        }
                        tool_results.append(formatted_result)

                        # Aggregate tool results
                        if tool_result.get('status') == 'success':
                            logger.info(f"[AGENT EXECUTION] Tool {tool.name} executed successfully")
                            aggregated_data['successful_tools'] += 1
                            if 'data' in tool_result:
                                aggregated_data['data_points'].append({
                                    'tool': tool.name,
                                    'data': tool_result['data']
                                })
                        else:
                            logger.warning(f"[AGENT EXECUTION] Tool {tool.name} execution failed")
                            aggregated_data['failed_tools'] += 1
                            if 'message' in tool_result:
                                aggregated_data['errors'].append({
                                    'tool': tool.name,
                                    'error': tool_result['message']
                                })

                    except Exception as tool_error:
                        logger.error(f"[AGENT EXECUTION] Error executing tool {tool.name}: {str(tool_error)}", exc_info=True)
                        tool_results.append({
                            "tool_name": tool.name,
                            "status": "failed",
                            "result": {
                                "tool_id": None,
                                "tool_name": tool.name,
                                "tool_type": tool.type,
                                "status": "failed",
                                "message": f"Failed to execute tool: {str(tool_error)}"
                            }
                        })
                        aggregated_data['failed_tools'] += 1
                        aggregated_data['errors'].append({
                            'tool': tool.name,
                            'error': str(tool_error)
                        })

            # Validate aggregated results with LLM
            validation_prompt = f"""As {self.name}, I have executed the following task:
Task Description: {task_description}

Requirements:
{json.dumps(requirements, indent=2)}

Tool Execution Summary:
- Successful Tools: {aggregated_data['successful_tools']}
- Failed Tools: {aggregated_data['failed_tools']}

Data Points Collected:
{json.dumps(aggregated_data['data_points'], indent=2)}

Errors Encountered:
{json.dumps(aggregated_data['errors'], indent=2)}

Initial Analysis:
{initial_llm_response}

Please validate the results and provide:
1. Whether the task requirements were met
2. A comprehensive analysis of the data collected
3. Any issues or concerns that need attention
4. Recommendations for next steps
"""

            logger.debug("[AGENT EXECUTION] Getting validation from LLM")
            # Get LLM validation
            validation_response = openai.ChatCompletion.create(
                model=self.foundation_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": validation_prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Extract validation response
            validation_llm_response = validation_response.choices[0].message.content
            logger.info("[AGENT EXECUTION] Received validation from LLM")
            logger.debug(f"[AGENT EXECUTION] Validation response: {validation_llm_response}")

            # For simple queries where no tools were needed, use the initial response
            if not tools_needed:
                logger.info("[AGENT EXECUTION] No tools were needed for this task")
                return {
                    'status': 'success',
                    'message': f"Agent {self.name} processed the task",
                    'initial_analysis': initial_llm_response,
                    'tool_results': [],
                    'aggregated_data': aggregated_data,
                    'validation_result': initial_llm_response,
                    'llm_response': initial_llm_response
                }

            # Determine final status based on validation
            final_status = 'success' if (
                aggregated_data['successful_tools'] > 0 and 
                'requirements were met' in validation_llm_response.lower()
            ) else 'failed'

            logger.info(f"[AGENT EXECUTION] Task completed with status: {final_status}")
            return {
                'status': final_status,
                'message': f"Agent {self.name} processed the task",
                'initial_analysis': initial_llm_response,
                'tool_results': tool_results,
                'aggregated_data': aggregated_data,
                'validation_result': validation_llm_response,
                'llm_response': validation_llm_response  # Use validation as final response
            }
        except Exception as e:
            logger.error(f"[AGENT EXECUTION] Error executing tools: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'message': str(e),
                'llm_response': None,
                'tool_results': [],
                'aggregated_data': {
                    'successful_tools': 0,
                    'failed_tools': 0,
                    'data_points': [],
                    'errors': [{'error': str(e)}]
                },
                'validation_result': None
            }

    def _execute_tool(self, tool: AgentTool, task_description: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool based on its type"""
        try:
            if re.search(r"github", tool.type, re.IGNORECASE):
                return self._execute_github_tool(tool, requirements)
            elif re.search(r"database", tool.type, re.IGNORECASE):
                return self._execute_database_tool(tool, task_description)
            else:
                return {
                    'status': 'failed',
                    'message': f"Unsupported tool type: {tool.type}"
                }
        except Exception as e:
            logger.error(f"Error in tool execution: {str(e)}", exc_info=True)
            return {
                'status': 'failed',
                'message': str(e)
            }

    def _execute_github_tool(self, tool: AgentTool, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a GitHub tool command"""
        try:
            logger.info(f"[GITHUB TOOL] Starting GitHub tool execution for tool {tool.name}")
            
            # Get task description from requirements
            task_description = requirements.get('task_description', '')
            logger.debug(f"[GITHUB TOOL] Task description: {task_description}")
            
            # Create GitHub tool instance
            logger.debug("[GITHUB TOOL] Creating GitHubTool instance...")
            github_tool = GitHubTool(
                tool_id=0,  # Temporary ID
                tool_name=tool.name,
                hostname="github.com",
                username="",
                password="",
                auth_method="none",
                description=tool.description
            )
            logger.info("[GITHUB TOOL] GitHubTool instance created successfully")
            
            # Execute the tool with the task description
            logger.debug("[GITHUB TOOL] Executing GitHub tool...")
            result = github_tool.execute(task_description)
            
            if result.get('status') == 'error':
                logger.warning(f"[GITHUB TOOL] Error executing GitHub tool: {result.get('message')}")
                return result
            
            logger.info("[GITHUB TOOL] GitHub tool execution completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"[GITHUB TOOL] Error executing GitHub tool: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error executing GitHub tool: {str(e)}'
            }

    def _execute_database_tool(self, tool: AgentTool, query: str) -> Dict[str, Any]:
        """Execute database operations"""
        try:
            # Simulate database query
            return {
                'status': 'success',
                'tool_id': 202,  # Example tool ID
                'hostname': 'db-server',
                'auth_method': 'Password',
                'command': 'SELECT COUNT(*) FROM nfl_favorite_team',
                'data': {
                    'database_specific': {
                        'query_type': 'simulated',
                        'affected_rows': 32,
                        'execution_time': '0.02s'
                    }
                }
            }
        except Exception as e:
            return {
                'status': 'failed',
                'message': f"Database tool execution failed: {str(e)}"
            } 