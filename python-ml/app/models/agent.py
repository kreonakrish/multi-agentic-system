from typing import Dict, Any, List, Optional
from datetime import datetime
from app.utils.enums import AgentStatus
from app.utils.logger import logger
from app.config.openai_config import get_openai_client
from app.core.tools import Tool, GitHubTool, DatabaseTool, APITool, WebServiceTool, PythonTool, ReactTool
import json
import re

class Agent:
    """Data model for an agent"""
    
    def __init__(
        self,
        agent_id: int,
        name: str,
        memory_type: str,
        foundation_model: str,
        team_id: Optional[int] = None,
        use_prod: bool = False
    ):
        self.agent_id = agent_id
        self.name = name
        self.memory_type = memory_type
        self.foundation_model = foundation_model
        self.team_id = team_id
        self.use_prod = use_prod
        self.tools: List[Tool] = []
        self.status = AgentStatus.IDLE.value
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.correlation_id = None
        self.metrics = {
            'total_interactions': 0,
            'successful_interactions': 0,
            'failed_interactions': 0,
            'average_response_time': 0
        }
        self.memories = []
        self.team_config = None
        self._openai = None  # Lazy-loaded OpenAI client

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
            'tools': [{'name': t.tool_name, 'description': t.description, 'type': t.type} for t in self.tools],
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
                use_prod=data.get('use_prod', False)
            )
            # Convert tool dictionaries to Tool objects
            for tool_data in data.get('tools', []):
                agent.add_tool(tool_data['tool_id'], tool_data['tool_name'], tool_data['type'], tool_data['hostname'], tool_data['username'], tool_data['password'], tool_data['auth_method'], tool_data['description'])
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

    def add_tool(self, tool_id: int, tool_name: str, tool_type: str, hostname: str, username: str = "", password: str = "", auth_method: str = "none", description: str = "") -> None:
        """Add a tool to the agent"""
        # Create the appropriate tool instance based on type
        tool: Optional[Tool] = None
        
        if tool_type.lower() == "github":
            tool = GitHubTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type.lower() == "database":
            tool = DatabaseTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type.lower() == "api":
            tool = APITool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type.lower() == "webservice":
            tool = WebServiceTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type.lower() == "python":
            tool = PythonTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type.lower() == "react":
            tool = ReactTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        else:
            logger.warning(f"Unknown tool type: {tool_type}, using base Tool class")
            tool = Tool(tool_id, tool_name, hostname, username, password, auth_method, description)
        
        if tool:
            self.tools.append(tool)
            logger.info(f"Tool {tool_name} (type: {tool_type}) added to agent {self.agent_id}")

    def remove_tool(self, tool_id: int) -> None:
        """Remove a tool from the agent by ID"""
        self.tools = [t for t in self.tools if t.tool_id != tool_id]
        self.updated_at = datetime.utcnow()
        logger.info(f"Tool {tool_id} removed from agent {self.agent_id}")

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
            
            logger.info(f"[AGENT] Agent {self.agent_id} starting task execution")
            logger.info(f"[AGENT] Task Description: {task_description}")
            logger.debug(f"[AGENT] Requirements: {json.dumps(requirements, indent=2)}")
            
            # Log available tools
            tools_desc = "\n".join([f"- {t.tool_name}: {t.description}" for t in self.tools])
            logger.info(f"[AGENT] Available tools:\n{tools_desc}")
            
            # First, check if this is a GitHub data request
            github_tool = next((t for t in self.tools if isinstance(t, GitHubTool)), None)
            if github_tool:
                # Try to extract dataset name
                dataset_name = github_tool._extract_dataset_name_from_text(task_description)
                if dataset_name:
                    logger.info(f"[AGENT] Found GitHub dataset request: {dataset_name}")
                    result = github_tool.execute(task_description)
                    if result['status'] == 'success':
                        return {
                            'status': 'success',
                            'message': 'GitHub data retrieved successfully',
                            'response': {
                                'message': result.get('message', ''),
                                'data': result.get('data', {}),
                                'tool_results': [{
                                    'tool_name': github_tool.tool_name,
                                    'result': result
                                }],
                                'llm_response': result.get('llm_response', ''),
                                'vector_store_results': result.get('vector_store_results', []),
                                'raw_data': result.get('raw_data', {})
                            }
                        }
            
            # Execute with each tool
            tool_results = []
            aggregated_vector_results = []
            raw_data_samples = []
            
            for tool in self.tools:
                try:
                    result = tool.execute(task_description)
                    if result['status'] == 'success':
                        tool_results.append({
                            'tool_name': tool.tool_name,
                            'result': result
                        })
                        
                        # Collect vector store results and raw data if available
                        if 'aggregation_data' in result:
                            agg_data = result['aggregation_data']
                            if 'vector_store' in agg_data:
                                aggregated_vector_results.append({
                                    'tool': tool.tool_name,
                                    'query': agg_data['vector_store']['query'],
                                    'results': agg_data['vector_store']['results']
                                })
                            if 'raw_data' in agg_data:
                                raw_data_samples.append({
                                    'tool': tool.tool_name,
                                    'sample': agg_data['raw_data']['sample'],
                                    'total_records': agg_data['raw_data']['total_records'],
                                    'schema': agg_data['raw_data']['schema']
                                })
                
                except Exception as e:
                    logger.error(f"[AGENT] Error executing tool {tool.tool_name}: {str(e)}")
                    tool_results.append({
                        'tool_name': tool.tool_name,
                        'error': str(e)
                    })
            
            # Aggregate and validate results using LLM
            aggregation_prompt = f"""
            Task Description: {task_description}
            
            Tool Results Summary:
            {json.dumps(tool_results, indent=2)}
            
            Vector Store Results:
            {json.dumps(aggregated_vector_results, indent=2)}
            
            Raw Data Samples:
            {json.dumps(raw_data_samples, indent=2)}
            
            Please analyze these results and provide:
            1. A comprehensive summary of findings
            2. Key insights from vector store searches
            3. Relevant patterns from raw data samples
            4. Any discrepancies or potential issues
            5. Confidence level in the results
            """
            
            # Get aggregated analysis from LLM
            aggregation_response = openai.chat.completions.create(
                model=self.foundation_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing and synthesizing tool results and data findings."},
                    {"role": "user", "content": aggregation_prompt}
                ],
                temperature=0.3
            )
            
            aggregated_analysis = aggregation_response.choices[0].message.content
            
            # Return final response
            return {
                'status': 'success',
                'message': 'Task executed successfully',
                'response': {
                    'message': 'Task executed successfully',
                    'data': {},
                    'tool_results': tool_results,
                    'llm_response': aggregated_analysis,
                    'vector_store_results': aggregated_vector_results,
                    'raw_data': {
                        'samples': raw_data_samples,
                        'total_records': sum(s.get('total_records', 0) for s in raw_data_samples),
                        'schemas': [s.get('schema') for s in raw_data_samples if s.get('schema')]
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"[AGENT] Error in execute_with_tools: {str(e)}")
            return {
                'status': 'error',
                'message': f'Failed to execute tools: {str(e)}',
                'response': {
                    'message': str(e),
                    'data': {},
                    'tool_results': [],
                    'llm_response': '',
                    'vector_store_results': [],
                    'raw_data': {
                        'samples': [],
                        'total_records': 0,
                        'schemas': []
                    }
                }
            } 