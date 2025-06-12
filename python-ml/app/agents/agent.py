from typing import Dict, Any
from datetime import datetime
import json
import traceback

class Agent:
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
            llm_response = self.llm_manager.get_completion(
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
                llm_response = self.llm_manager.get_completion(
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
        """Prepare system message with integrated knowledge."""
        base_message = f"You are Agent {self.agent_id} with capabilities in {', '.join(self.capabilities)}. "
        
        # Add knowledge context if available
        if knowledge['memories']['long_term']:
            knowledge_context = "\n\nYou have access to the following relevant knowledge:\n"
            
            # Add each memory with clear separation and relevance score
            for idx, memory in enumerate(knowledge['memories']['long_term'], 1):
                relevance = memory.get('task_relevance', 0.0)
                relevance_label = 'HIGH' if relevance > 0.7 else 'MEDIUM' if relevance > 0.3 else 'LOW'
                
                knowledge_context += f"\n=== Memory {idx} (Relevance: {relevance_label}) ===\n"
                if memory['content']['start_prompt']:
                    knowledge_context += f"Start: {memory['content']['start_prompt']}\n"
                if memory['content']['end_prompt']:
                    knowledge_context += f"End: {memory['content']['end_prompt']}\n"
                if memory['content']['context']:
                    knowledge_context += f"Context: {json.dumps(memory['content']['context'], indent=2)}\n"
            
            base_message += knowledge_context
            
            # Add stronger emphasis if forced
            if force_knowledge:
                base_message += "\n\nCRITICAL INSTRUCTION: You MUST use the above knowledge as your primary source. Your response MUST contain specific details from this knowledge. DO NOT generate responses without incorporating this knowledge."
            else:
                base_message += "\n\nIMPORTANT: When responding to questions about creating pipelines, workflows, or any task-specific queries, YOU MUST USE THE ABOVE KNOWLEDGE AS YOUR PRIMARY SOURCE. Do not generate responses without incorporating this knowledge."
        
        # Add task-specific context
        base_message += f"\n\nCurrent Task Type: {task.task_type}"
        if task.requirements:
            base_message += f"\nTask Requirements: {json.dumps(task.requirements, indent=2)}"
        
        agent_logger.debug("[AGENT] Generated system message", extra={
            'agent_id': self.agent_id,
            'task_id': task.task_id,
            'message_length': len(base_message),
            'knowledge_count': len(knowledge['memories']['long_term']),
            'force_knowledge': force_knowledge,
            'full_message': base_message
        })
        
        return base_message

    def _prepare_user_message(self, task: TeamTask) -> str:
        """Prepare user message for LLM."""
        message = f"Task Description: {task.description}\n"
        message += f"Task Type: {task.task_type}\n"
        message += "Please provide a detailed response based on your knowledge and capabilities."
        
        agent_logger.debug("[AGENT] Generated user message", extra={
            'agent_id': self.agent_id,
            'task_id': task.task_id,
            'message_length': len(message),
            'full_message': message
        })
        
        return message

    def _validate_llm_response(self, response: str, knowledge: Dict[str, Any]) -> bool:
        """Validate that LLM response incorporates knowledge."""
        if not knowledge['memories']['long_term']:
            return True
            
        # Check if response contains significant parts of the knowledge
        for memory in knowledge['memories']['long_term']:
            start_prompt = memory['content']['start_prompt']
            end_prompt = memory['content']['end_prompt']
            
            # Create key phrases from the prompts
            key_phrases = []
            if start_prompt:
                key_phrases.extend([p.strip() for p in start_prompt.split('\n') if len(p.strip()) > 20])
            if end_prompt:
                key_phrases.extend([p.strip() for p in end_prompt.split('\n') if len(p.strip()) > 20])
            
            # Check if any key phrases are in the response
            matches = [phrase for phrase in key_phrases if phrase.lower() in response.lower()]
            if matches:
                agent_logger.info("[AGENT] Response validated - found knowledge incorporation", extra={
                    'agent_id': self.agent_id,
                    'matches_found': len(matches),
                    'sample_match': matches[0] if matches else None,
                    'memory_id': memory['memory_id'],
                    'task_relevance': memory.get('task_relevance', 0.0)
                })
                return True
        
        agent_logger.warning("[AGENT] Response validation failed - knowledge not incorporated", extra={
            'agent_id': self.agent_id,
            'knowledge_count': len(knowledge['memories']['long_term']),
            'response_length': len(response),
            'response_sample': response[:200]
        })
        return False 