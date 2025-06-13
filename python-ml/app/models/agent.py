from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from app.utils.enums import AgentStatus
from app.utils.logger import logger, agent_logger, knowledge_retrieve_logger, knowledge_llm_logger, knowledge_metrics_logger
from app.config.openai_config import get_openai_client
from app.core.tools import Tool, GitHubTool, DatabaseTool, APITool, WebServiceTool, PythonTool, ReactTool
from app.utils.db import get_db_connection, safe_close_connection
from app.models.task import TeamTask
import json
import re
import traceback
import uuid

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
        self.knowledge_manager = None  # Will be set by the workflow manager
        self._capabilities = []  # List of agent capabilities

    @property
    def capabilities(self) -> List[str]:
        """Get agent capabilities based on tools."""
        return [t.__class__.__name__.replace('Tool', '').lower() for t in self.tools] if self.tools else ["general"]

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
            'tools': [t.to_dict() for t in self.tools],
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
        from app.core.tools import (
            GitHubTool, DatabaseTool, APITool, WebServiceTool,
            PythonTool, ReactTool
        )
        
        tool_type = tool_type.lower().replace("_", "").replace("-", "")
        
        if tool_type == "github":
            tool = GitHubTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type == "database":
            tool = DatabaseTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type in ["api", "apiservice"]:
            tool = APITool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type == "webservice":
            tool = WebServiceTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type == "python":
            tool = PythonTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        elif tool_type == "react":
            tool = ReactTool(tool_id, tool_name, hostname, username, password, auth_method, description)
        else:
            logger.warning(f"Unknown tool type: {tool_type}, defaulting to APITool")
            tool = APITool(tool_id, tool_name, hostname, username, password, auth_method, description)
        
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

    def _check_predefined_response(self, task: TeamTask, knowledge: Dict[str, Any]) -> Optional[str]:
        """Check if there's a predefined response in agent memory."""
        try:
            # Check long-term memories first
            for memory in knowledge.get('memories', {}).get('long_term', []):
                if memory.get('source_type') == 'predefined':
                    # Get the context which contains success_patterns
                    context = memory.get('content', {}).get('context', {})
                    success_patterns = context.get('success_patterns', [])
                    
                    # Check each success pattern
                    for pattern in success_patterns:
                        # If the pattern contains instructions about the task type
                        if isinstance(pattern, str) and 'databricks pipeline' in pattern.lower():
                            agent_logger.info("[AGENT] Found predefined response in memory", extra={
                                'agent_id': self.agent_id,
                                'task_id': task.task_id,
                                'memory_id': memory.get('memory_id'),
                                'pattern_found': True
                            })
                            # Return the SQL statement from the pattern
                            return pattern
                            
            agent_logger.info("[AGENT] No predefined response found in memory", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'memory_count': len(knowledge.get('memories', {}).get('long_term', []))
            })
            return None
        except Exception as e:
            agent_logger.error(f"[AGENT] Error checking predefined response: {str(e)}", exc_info=True)
            return None

    def execute_with_tools(self, message: str) -> Dict[str, Any]:
        """Execute task with available tools and knowledge."""
        try:
            # Parse message
            try:
                message_data = json.loads(message)
                task_description = message_data.get('task_description', '')
                requirements = message_data.get('requirements', {})
                knowledge_context = message_data.get('knowledge_context', {})
            except json.JSONDecodeError:
                task_description = message
                requirements = {}
                knowledge_context = {}

            # Create a TeamTask object
            task = TeamTask(
                task_id=str(uuid.uuid4()),
                task_type=requirements.get('task_type', 'general'),
                complexity=requirements.get('complexity', 'medium'),
                description=task_description,
                requirements=requirements
            )
            
            # Get relevant knowledge
            if not knowledge_context and self.knowledge_manager:
                knowledge = self.knowledge_manager.get_relevant_knowledge(self.agent_id, task)
                agent_logger.info("[AGENT] Retrieved knowledge", extra={
                    'agent_id': self.agent_id,
                    'task_id': task.task_id,
                    'knowledge_count': len(knowledge['memories']['long_term']),
                    'knowledge_relevance': knowledge.get('task_relevance', {}),
                    'timestamp': datetime.now().isoformat()
                })
            else:
                knowledge = {
                    'memories': knowledge_context,
                    'source_counts': {},
                    'task_relevance': {}
                }
            
            # Check for predefined response first
            predefined_response = self._check_predefined_response(task, knowledge)
            if predefined_response:
                agent_logger.info("[AGENT] Using predefined response from memory", extra={
                    'agent_id': self.agent_id,
                    'task_id': task.task_id
                })
                return {
                    'status': 'success',
                    'response': {
                        'message': predefined_response,
                        'data': {},
                        'tool_results': [],
                        'llm_response': predefined_response,
                        'vector_store_results': [],
                        'raw_data': {'source': 'agent_memory'}
                    },
                    'confidence': 1.0,
                    'tool_usage': [],
                    'llm_communication_success': True
                }

            # If no predefined response, proceed with normal execution
            # Get OpenAI client
            openai = self.get_openai_client()
            
            # Add task description to requirements
            requirements['description'] = task_description
            
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
            
            # Prepare system message with knowledge integration
            system_message = self._prepare_system_message(task, knowledge)
            agent_logger.info("[AGENT] Prepared system message", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'system_message_length': len(system_message),
                'knowledge_integrated': bool(knowledge['memories']['long_term']),
                'full_system_message': system_message
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
            
            # Get aggregated analysis from LLM with knowledge context
            aggregation_response = openai.chat.completions.create(
                model=self.foundation_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": aggregation_prompt}
                ],
                temperature=0.3
            )
            
            aggregated_analysis = aggregation_response.choices[0].message.content
            
            # Validate that LLM used the knowledge
            if not self._validate_llm_response(aggregated_analysis, knowledge):
                agent_logger.warning("[AGENT] LLM response did not incorporate knowledge", extra={
                    'agent_id': self.agent_id,
                    'task_id': task.task_id,
                    'knowledge_count': len(knowledge['memories']['long_term']),
                    'response_length': len(aggregated_analysis)
                })
                
                # Retry with stronger emphasis on knowledge use
                system_message = self._prepare_system_message(task, knowledge, force_knowledge=True)
                aggregation_response = openai.chat.completions.create(
                    model=self.foundation_model,
                    messages=[
                        {"role": "system", "content": system_message},
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
                },
                'knowledge_used': knowledge['source_counts'],
                'task_relevance': knowledge.get('task_relevance', {})
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

    def execute_task(self, task: TeamTask) -> Dict[str, Any]:
        """Execute a task using the agent's capabilities."""
        try:
            # Get relevant knowledge
            knowledge = self.knowledge_manager.get_relevant_knowledge(self.agent_id, task)
            
            agent_logger.info("[AGENT] Starting task execution", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'task_type': task.task_type,
                'task_description': task.description,
                'knowledge_count': len(knowledge['memories']['long_term']),
                'knowledge_relevance': knowledge.get('task_relevance', {}),
                'timestamp': datetime.now().isoformat()
            })

            # Prepare system message with knowledge integration
            system_message = self._prepare_system_message(task, knowledge)
            agent_logger.info("[AGENT] Prepared system message", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'system_message_length': len(system_message),
                'knowledge_integrated': bool(knowledge['memories']['long_term']),
                'full_system_message': system_message
            })

            # Prepare user message
            user_message = self._prepare_user_message(task)
            agent_logger.info("[AGENT] Prepared user message", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'user_message_length': len(user_message),
                'full_user_message': user_message
            })

            # Call LLM with knowledge context
            llm_response = self.get_completion(
                system_message=system_message,
                user_message=user_message
            )
            
            # Validate that LLM used the knowledge
            if not self._validate_llm_response(llm_response, knowledge):
                agent_logger.warning("[AGENT] LLM response did not incorporate knowledge", extra={
                    'agent_id': self.agent_id,
                    'task_id': task.task_id,
                    'knowledge_count': len(knowledge['memories']['long_term']),
                    'response_length': len(llm_response)
                })
                
                # Retry with stronger emphasis on knowledge use
                system_message = self._prepare_system_message(task, knowledge, force_knowledge=True)
                llm_response = self.get_completion(
                    system_message=system_message,
                    user_message=user_message
                )
            
            agent_logger.info("[AGENT] Received LLM response", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'response_length': len(llm_response),
                'knowledge_used': self._validate_llm_response(llm_response, knowledge),
                'full_response': llm_response,
                'timestamp': datetime.now().isoformat()
            })

            return {
                'status': 'success',
                'response': llm_response,
                'knowledge_used': knowledge['source_counts'],
                'task_relevance': knowledge.get('task_relevance', {})
            }

        except Exception as e:
            agent_logger.error("[AGENT] Task execution failed", extra={
                'agent_id': self.agent_id,
                'task_id': task.task_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc(),
                'timestamp': datetime.now().isoformat()
            }, exc_info=True)
            
            return {
                'status': 'error',
                'error': str(e)
            }

    def _prepare_system_message(self, task: TeamTask, knowledge: Dict[str, Any], force_knowledge: bool = False) -> str:
        """Prepare system message for LLM with emphasis on agent memory."""
        try:
            # Extract memories from knowledge
            memories = knowledge.get('memories', {})
            long_term_memories = memories.get('long_term', [])
            short_term_memories = memories.get('short_term', [])
            
            # Build memory context
            memory_context = []
            
            # Add long-term memories first (highest priority)
            for memory in long_term_memories:
                if memory.get('source_type') == 'predefined':
                    memory_context.append(f"Predefined Knowledge (HIGHEST PRIORITY):\n{memory['content']['start_prompt']}")
                else:
                    # Extract key information from memory
                    memory_info = {
                        'memory_id': memory['memory_id'],
                        'confidence': memory['content'].get('confidence', 0.0),
                        'task_relevance': memory.get('task_relevance', 0.0),
                        'content': {
                            'start_prompt': memory['content'].get('start_prompt', ''),
                            'end_prompt': memory['content'].get('end_prompt', ''),
                            'context': memory['content'].get('context', {})
                        }
                    }
                    memory_context.append(f"Long-term Memory:\n{json.dumps(memory_info, indent=2)}")
            
            # Add short-term memories
            for memory in short_term_memories:
                memory_info = {
                    'memory_id': memory.get('memory_id', 'unknown'),
                    'content': memory.get('content', {}),
                    'confidence': memory.get('confidence', 0.0)
                }
                memory_context.append(f"Short-term Memory:\n{json.dumps(memory_info, indent=2)}")
            
            # Build system message
            system_message = f"""You are an AI agent with the following capabilities and knowledge:

1. AGENT MEMORY (HIGHEST PRIORITY):
{chr(10).join(memory_context) if memory_context else "No agent memory available."}

2. TASK REQUIREMENTS:
- Task Type: {task.task_type}
- Description: {task.description}
- Requirements: {json.dumps(task.requirements, indent=2)}

3. RESPONSE PRIORITY ORDER:
1. Use predefined responses from agent memory if available
2. Use relevant knowledge from agent memory
3. Use vector store results if needed
4. Use tool results as a last resort

4. IMPORTANT INSTRUCTIONS:
- ALWAYS check agent memory first for predefined responses
- If a predefined response exists in memory, use it without modification
- Only proceed to other knowledge sources if no predefined response exists
- Maintain high confidence in responses from agent memory
- Document the source of your response (agent_memory, vector_store, or tool_results)
- When using agent memory, explicitly reference the memory_id and confidence level
- Ensure your response incorporates key concepts and patterns from the memory
- If multiple memories are relevant, combine their insights while maintaining clarity

5. TOOLS AVAILABLE:
{json.dumps([t.to_dict() for t in self.tools], indent=2)}

CRITICAL INSTRUCTIONS FOR USING AGENT MEMORY:
1. CONTEXT UTILIZATION:
   - ALWAYS analyze the context from agent memory first
   - Extract and use relevant patterns, examples, and solutions from the context
   - If the context contains specific implementation details, use them as a template
   - Reference specific parts of the context in your response

2. KNOWLEDGE PRIORITIZATION:
   - Predefined knowledge takes absolute priority
   - Long-term memory with high confidence (>0.8) should be used as primary guidance
   - Combine insights from multiple memories when they are complementary
   - Always cite the memory_id when using specific knowledge

3. RESPONSE STRUCTURE:
   - Start by acknowledging which memories you're using
   - Explain how the context influences your response
   - Provide specific examples or patterns from the memory
   - Include confidence levels for each piece of knowledge used

4. VALIDATION REQUIREMENTS:
   - Your response MUST demonstrate clear use of agent memory
   - Include specific references to memory content
   - Show how you've adapted the knowledge to the current task
   - Explain any modifications made to the original knowledge

Remember: Agent memory knowledge takes precedence over all other sources. If you find a predefined response in memory, use it without modification.

KNOWLEDGE INCORPORATION GUIDELINES:
1. Start by identifying relevant memories based on task description
2. Extract key concepts and patterns from those memories
3. Structure your response to explicitly use these concepts
4. Include confidence levels and memory references
5. If no exact match exists, combine relevant insights from multiple memories
6. Always explain how you're using the knowledge in your response"""

            if force_knowledge:
                system_message += "\n\nCRITICAL: You MUST use the knowledge provided in agent memory. Do not generate responses without consulting the memory first. Your response will be validated to ensure knowledge incorporation."

            return system_message
        except Exception as e:
            agent_logger.error(f"[AGENT] Error preparing system message: {str(e)}", exc_info=True)
            return "You are an AI agent. Please process the task using available knowledge and tools."

    def _prepare_user_message(self, task: TeamTask) -> str:
        """Prepare user message for LLM."""
        message = f"""Task Description: {task.description}

Task Type: {task.task_type}

Please provide a detailed response that:
1. Explicitly references and uses knowledge from agent memory
2. Includes confidence levels for the knowledge used
3. Explains how the knowledge is being applied
4. Combines insights from multiple memories if relevant
5. Maintains clarity while incorporating knowledge

Your response will be validated to ensure proper knowledge incorporation."""
        
        agent_logger.debug("[AGENT] Generated user message", extra={
            'agent_id': self.agent_id,
            'task_id': task.task_id,
            'message_length': len(message),
            'full_message': message
        })
        
        return message

    def _validate_llm_response(self, response: str, knowledge: Dict[str, Any]) -> bool:
        """Validate that LLM response incorporates knowledge."""
        try:
            # Extract memories from knowledge
            memories = knowledge.get('memories', {})
            long_term_memories = memories.get('long_term', [])
            
            if not long_term_memories:
                return True  # No knowledge to validate against
            
            # Extract key concepts from memories
            key_concepts = set()
            for memory in long_term_memories:
                if memory.get('source_type') == 'predefined':
                    # For predefined knowledge, use the entire content
                    key_concepts.add(memory['content']['start_prompt'].lower())
                else:
                    # For other memories, extract key concepts from start_prompt and end_prompt
                    start_prompt = memory['content'].get('start_prompt', '').lower()
                    end_prompt = memory['content'].get('end_prompt', '').lower()
                    key_concepts.update(start_prompt.split())
                    key_concepts.update(end_prompt.split())
            
            # Remove common words and short terms
            key_concepts = {concept for concept in key_concepts if len(concept) > 3}
            
            # Check for knowledge incorporation
            response_lower = response.lower()
            matches = []
            
            # Check for exact matches
            for concept in key_concepts:
                if concept in response_lower:
                    matches.append(concept)
            
            # Calculate word overlap
            response_words = set(response_lower.split())
            overlap = len(response_words.intersection(key_concepts)) / len(key_concepts) if key_concepts else 0
            
            # Log validation results
            agent_logger.info("[AGENT] Validating LLM response", extra={
                'agent_id': self.agent_id,
                'key_concepts_count': len(key_concepts),
                'matches_found': len(matches),
                'word_overlap': overlap,
                'sample_matches': matches[:5] if matches else []
            })
            
            # Consider the response valid if:
            # 1. There are exact matches, or
            # 2. The word overlap is above 70%
            is_valid = len(matches) > 0 or overlap > 0.7
            
            if not is_valid:
                agent_logger.warning("[AGENT] LLM response validation failed", extra={
                    'agent_id': self.agent_id,
                    'matches_found': len(matches),
                    'word_overlap': overlap,
                    'key_concepts': list(key_concepts)[:10]
                })
            
            return is_valid
            
        except Exception as e:
            agent_logger.error(f"[AGENT] Error validating LLM response: {str(e)}", exc_info=True)
            return True  # Default to True on error to avoid blocking responses

    def get_completion(self, system_message: str, user_message: str) -> str:
        """Get completion from OpenAI."""
        try:
            openai = self.get_openai_client()
            response = openai.chat.completions.create(
                model=self.foundation_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            agent_logger.error("[AGENT] Error getting LLM completion", extra={
                'agent_id': self.agent_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            }, exc_info=True)
            raise