"""Knowledge manager for handling agent memories and knowledge graph."""
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime
import json
from app.models.task import TeamTask
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.json_encoder import CustomJSONEncoder
import traceback
from app.utils.logger import (
    knowledge_store_logger,
    knowledge_retrieve_logger,
    knowledge_llm_logger,
    knowledge_metrics_logger,
    workflow_logger,
)


class KnowledgeManager:
    """Manages agent knowledge and memory."""
    
    def __init__(self):
        """Initialize knowledge manager."""
        self.db_conn = None
        self._ensure_db_connection()

    def _ensure_db_connection(self):
        """Ensure database connection is valid, reconnecting if necessary."""
        try:
            # First check if we need to establish a new connection
            if self.db_conn is None:
                self.db_conn = get_db_connection()
                knowledge_store_logger.info("[KNOWLEDGE] New database connection established")
                return

            # If we have a connection, validate it
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                knowledge_store_logger.debug("[KNOWLEDGE] Existing database connection is valid")
            except Exception as e:
                knowledge_store_logger.warning("[KNOWLEDGE] Existing connection is invalid, reconnecting", extra={
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                # Close the invalid connection
                try:
                    self.db_conn.close()
                except:
                    pass
                # Get a new connection
                self.db_conn = get_db_connection()
                knowledge_store_logger.info("[KNOWLEDGE] Database connection reestablished")

        except Exception as e:
            knowledge_store_logger.error("[KNOWLEDGE] Failed to establish database connection", extra={
                'error': str(e),
                'error_type': type(e).__name__
            })
            self.db_conn = None  # Reset connection on failure
            raise

    def __del__(self):
        """Cleanup database connection."""
        if hasattr(self, 'db_conn') and self.db_conn is not None:
            safe_close_connection(self.db_conn)

    def store_task_knowledge(self, agent_id: int, task: TeamTask, 
                           execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store knowledge gained from task execution in agent memory.
        
        Args:
            agent_id: ID of the agent
            task: The executed task
            execution_result: Results from task execution
            
        Returns:
            Dictionary containing stored memory information
        """
        try:
            knowledge_store_logger.info("[KNOWLEDGE] Starting knowledge storage", extra={
                'agent_id': agent_id,
                'task_id': task.task_id,
                'task_type': task.task_type,
                'execution_status': execution_result.get('status'),
                'timestamp': datetime.now().isoformat()
            })
            
            # Extract knowledge from execution result
            knowledge = self._extract_knowledge(task, execution_result)
            
            knowledge_store_logger.info("[KNOWLEDGE] Knowledge extracted", extra={
                'agent_id': agent_id,
                'task_id': task.task_id,
                'knowledge_type': knowledge['task_type'],
                'tools_used': knowledge['tools_used'],
                'success_patterns_count': len(knowledge['success_patterns']),
                'error_patterns_count': len(knowledge['error_patterns']),
                'context_size': len(json.dumps(knowledge['context']))
            })
            
            # Store as different memory types
            memory_ids = {
                'long_term': self._store_long_term_memory(agent_id, knowledge),
                'short_term': self._store_short_term_memory(agent_id, knowledge),
                'graph': self._store_graph_memory(agent_id, knowledge),
                'json': self._store_json_memory(agent_id, knowledge)
            }
            
            knowledge_store_logger.info("[KNOWLEDGE] Memory storage completed", extra={
                'agent_id': agent_id,
                'task_id': task.task_id,
                'memory_ids': memory_ids,
                'storage_types': list(memory_ids.keys()),
                'storage_success': all(id > 0 for id in memory_ids.values())
            })
            
            # Log metrics about stored knowledge
            knowledge_metrics_logger.info("[METRICS] Knowledge storage metrics", extra={
                'agent_id': agent_id,
                'task_id': task.task_id,
                'memory_types_stored': len(memory_ids),
                'knowledge_size': len(json.dumps(knowledge)),
                'tools_count': len(knowledge['tools_used']),
                'patterns_stored': len(knowledge['success_patterns']) + len(knowledge['error_patterns']),
                'storage_timestamp': datetime.now().isoformat()
            })
            
            return {
                'status': 'success',
                'memory_ids': memory_ids,
                'knowledge_extracted': knowledge
            }
            
        except Exception as e:
            knowledge_store_logger.error("[KNOWLEDGE] Error storing knowledge", extra={
                'agent_id': agent_id,
                'task_id': task.task_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }, exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_relevant_knowledge(self, agent_id: int, task: Union[TeamTask, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get relevant knowledge for a task.
        
        Args:
            agent_id: The agent ID
            task: Either a TeamTask object or a dictionary containing task details
            
        Returns:
            Dictionary containing relevant knowledge with the following structure:
            {
                'memories': {
                    'long_term': List[Dict],
                    'short_term': List[Dict],
                    'graph': List[Dict],
                    'json': List[Dict]
                },
                'source_counts': Dict[str, int]
            }
        """
        try:
            # Extract task details based on input type
            if isinstance(task, TeamTask):
                task_id = task.task_id
                description = task.description
                requirements = task.requirements
            else:
                task_id = task.get('id')
                description = task.get('description', '')
                requirements = task.get('requirements', {})
            
            workflow_logger.info("[WORKFLOW] Getting relevant knowledge", extra={
                'agent_id': agent_id,
                'task_id': task_id,
                'description': description[:100] + '...' if len(description) > 100 else description
            })
            
            # Get agent's memories
            memories = self._get_agent_memories(agent_id)
            
            # Get relevant memories
            relevant_memories = self._find_relevant_memories(
                memories,
                description,
                requirements
            )
            
            # Get source counts
            source_counts = self._count_memory_sources(relevant_memories)
            
            # Store knowledge retrieval
            self._store_knowledge_retrieval(
                agent_id=agent_id,
                task_id=task_id,
                description=description,
                requirements=requirements,
                memory_count=len(relevant_memories),
                source_counts=source_counts
            )
            
            # Structure the response
            return {
                'memories': {
                    'long_term': relevant_memories,
                    'short_term': [],
                    'graph': [],
                    'json': []
                },
                'source_counts': source_counts
            }
            
        except Exception as e:
            workflow_logger.error(f"Error getting relevant knowledge: {str(e)}", exc_info=True)
            return {
                'memories': {
                    'long_term': [],
                    'short_term': [],
                    'graph': [],
                    'json': []
                },
                'source_counts': {}
            }

    def _calculate_task_relevance(self, task_description: str, start_prompt: Optional[str], end_prompt: Optional[str]) -> float:
        """Calculate relevance score between task and memory."""
        try:
            if not start_prompt and not end_prompt:
                return 0.0
                
            # Normalize text
            task_words = set(task_description.lower().split())
            memory_words = set((start_prompt or '').lower().split() + (end_prompt or '').lower().split())
            
            # Calculate word overlap
            common_words = task_words.intersection(memory_words)
            total_words = task_words.union(memory_words)
            
            if not total_words:
                return 0.0
                
            # Calculate Jaccard similarity
            return len(common_words) / len(total_words)
            
        except Exception:
            return 0.0

    def _parse_and_validate_context(self, context_data: Any, memory_id: int) -> Dict[str, Any]:
        """Parse and validate context data with enhanced error handling."""
        try:
            if not context_data:
                return {}
                
            if isinstance(context_data, dict):
                return context_data
                
            if isinstance(context_data, str):
                try:
                    # Try to parse as JSON
                    parsed_data = json.loads(context_data)
                    if isinstance(parsed_data, dict):
                        return parsed_data
                    return {'raw_data': parsed_data}
                except json.JSONDecodeError:
                    # Try to parse as stringified JSON
                    try:
                        # Remove escaped quotes and try again
                        cleaned_data = context_data.replace('\\"', '"').strip('"')
                        parsed_data = json.loads(cleaned_data)
                        if isinstance(parsed_data, dict):
                            return parsed_data
                        return {'raw_data': parsed_data}
                    except json.JSONDecodeError:
                        # If not valid JSON, store as raw text
                        return {'raw_text': context_data}
                    
            # For any other type, convert to string representation
            return {'raw_data': str(context_data)}
            
        except Exception as e:
            knowledge_retrieve_logger.error("[KNOWLEDGE] Context parsing error", extra={
                'memory_id': memory_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'raw_context': str(context_data)[:200] if context_data else None,
                'traceback': traceback.format_exc()
            })
            return {'error': str(e)}

    def _validate_memory_content(self, memory: Tuple) -> bool:
        """Validate memory content structure."""
        try:
            # Check for required fields
            if len(memory) < 7:
                return False
                
            # Validate memory type
            if not memory[1] or not isinstance(memory[1], str):
                return False
                
            # Validate that at least one prompt exists
            if not (memory[2] or memory[3]):
                return False
                
            # Validate confidence score
            try:
                confidence = float(memory[5]) if memory[5] else 0.0
                if confidence < 0 or confidence > 1:
                    return False
            except (ValueError, TypeError):
                return False
                
            return True
            
        except Exception as e:
            knowledge_retrieve_logger.error("[KNOWLEDGE] Memory validation error", extra={
                'memory_id': memory[0] if memory else None,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc()
            })
            return False

    def _validate_memory_structure(self, memory_content: Dict[str, Any]) -> bool:
        """Validate memory content structure before sending to LLM."""
        try:
            required_fields = ['start_prompt', 'end_prompt', 'context', 'confidence', 'source_type']
            
            # Check all required fields exist
            if not all(field in memory_content for field in required_fields):
                return False
                
            # Validate prompts
            if not isinstance(memory_content['start_prompt'], str) or not isinstance(memory_content['end_prompt'], str):
                return False
                
            # Validate context is dict
            if not isinstance(memory_content['context'], dict):
                return False
                
            # Validate confidence
            if not isinstance(memory_content['confidence'], (int, float)) or not 0 <= memory_content['confidence'] <= 1:
                return False
                
            return True
            
        except Exception as e:
            knowledge_retrieve_logger.error("[KNOWLEDGE] Memory structure validation error", extra={
                'error': str(e),
                'error_type': type(e).__name__,
                'memory_content': str(memory_content)[:200],
                'traceback': traceback.format_exc()
            })
            return False

    def _extract_knowledge(self, task: TeamTask, 
                         execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract knowledge from task execution result."""
        knowledge_store_logger.info("[KNOWLEDGE] Starting knowledge extraction", extra={
            'task_id': task.task_id,
            'task_type': task.task_type,
            'execution_status': execution_result.get('status'),
            'has_tools': bool(execution_result.get('tools_used')),
            'has_metrics': bool(execution_result.get('performance_metrics'))
        })
        
        knowledge = {
            'task_type': self._identify_task_type(task),
            'tools_used': execution_result.get('tools_used', []),
            'success_patterns': self._extract_success_patterns(execution_result),
            'error_patterns': self._extract_error_patterns(execution_result),
            'performance_metrics': execution_result.get('performance_metrics', {}),
            'context': {
                'task_description': task.description,
                'requirements': task.requirements,
                'execution_time': execution_result.get('execution_time'),
                'success_rate': execution_result.get('success_rate')
            }
        }
        
        knowledge_store_logger.info("[KNOWLEDGE] Knowledge extraction completed", extra={
            'task_id': task.task_id,
            'identified_type': knowledge['task_type'],
            'tools_count': len(knowledge['tools_used']),
            'success_patterns': len(knowledge['success_patterns']),
            'error_patterns': len(knowledge['error_patterns']),
            'has_metrics': bool(knowledge['performance_metrics']),
            'context_size': len(json.dumps(knowledge['context']))
        })
        
        return knowledge

    def _store_long_term_memory(self, agent_id: int, knowledge: Dict[str, Any]) -> int:
        """Store long-term memory in agent_memory table."""
        knowledge_store_logger.info("[KNOWLEDGE] Storing long-term memory", extra={
            'agent_id': agent_id,
            'knowledge_type': knowledge['task_type'],
            'context_size': len(json.dumps(knowledge['context'])),
            'patterns_count': len(knowledge['success_patterns'])
        })
        
        memory_id = self._store_memory(agent_id, 'LONG_TERM_MEMORY', knowledge, {
            'start_prompt': knowledge['context']['task_description'],
            'end_prompt': json.dumps(knowledge['success_patterns']),
            'context': json.dumps(knowledge),
            'source_type': 'task',
            'confidence': self._calculate_confidence(knowledge)
        })
        
        knowledge_store_logger.info("[KNOWLEDGE] Long-term memory stored", extra={
            'agent_id': agent_id,
            'memory_id': memory_id,
            'memory_type': 'LONG_TERM_MEMORY',
            'confidence': self._calculate_confidence(knowledge)
        })
        
        return memory_id

    def _store_short_term_memory(self, agent_id: int, knowledge: Dict[str, Any]) -> int:
        """Store short-term memory in agent_memory table."""
        knowledge_store_logger.info("[KNOWLEDGE] Storing short-term memory", extra={
            'agent_id': agent_id,
            'knowledge_type': knowledge['task_type'],
            'metrics_count': len(knowledge['performance_metrics'])
        })
        
        memory_id = self._store_memory(agent_id, 'SHORT_TERM_MEMORY', knowledge, {
            'start_prompt': knowledge['context']['task_description'],
            'end_prompt': json.dumps(knowledge['performance_metrics']),
            'context': json.dumps(knowledge['context']),
            'source_type': 'task',
            'confidence': self._calculate_confidence(knowledge)
        })
        
        knowledge_store_logger.info("[KNOWLEDGE] Short-term memory stored", extra={
            'agent_id': agent_id,
            'memory_id': memory_id,
            'memory_type': 'SHORT_TERM_MEMORY',
            'confidence': self._calculate_confidence(knowledge)
        })
        
        return memory_id

    def _store_graph_memory(self, agent_id: int, knowledge: Dict[str, Any]) -> int:
        """Store graph memory in agent_memory table."""
        # Create graph relationships
        relationships = {
            'task_type': knowledge['task_type'],
            'tools': knowledge['tools_used'],
            'patterns': {
                'success': knowledge['success_patterns'],
                'error': knowledge['error_patterns']
            }
        }
        
        knowledge_store_logger.info("[KNOWLEDGE] Storing graph memory", extra={
            'agent_id': agent_id,
            'knowledge_type': knowledge['task_type'],
            'relationship_types': list(relationships.keys()),
            'tools_count': len(relationships['tools'])
        })
        
        memory_id = self._store_memory(agent_id, 'GRAPH', knowledge, {
            'start_prompt': knowledge['context']['task_description'],
            'end_prompt': json.dumps(relationships),
            'context': json.dumps(knowledge),
            'source_type': 'task',
            'confidence': self._calculate_confidence(knowledge),
            'relationships': json.dumps(relationships)
        })
        
        knowledge_store_logger.info("[KNOWLEDGE] Graph memory stored", extra={
            'agent_id': agent_id,
            'memory_id': memory_id,
            'memory_type': 'GRAPH',
            'relationship_count': len(relationships),
            'confidence': self._calculate_confidence(knowledge)
        })
        
        return memory_id

    def _store_json_memory(self, agent_id: int, knowledge: Dict[str, Any]) -> int:
        """Store JSON memory in agent_memory table."""
        metadata = {
            'task_type': knowledge['task_type'],
            'tools_used': knowledge['tools_used'],
            'metrics': knowledge['performance_metrics']
        }
        
        knowledge_store_logger.info("[KNOWLEDGE] Storing JSON memory", extra={
            'agent_id': agent_id,
            'knowledge_type': knowledge['task_type'],
            'metadata_keys': list(metadata.keys()),
            'tools_count': len(metadata['tools_used'])
        })
        
        memory_id = self._store_memory(agent_id, 'JSON', knowledge, {
            'start_prompt': knowledge['context']['task_description'],
            'end_prompt': json.dumps(knowledge['performance_metrics']),
            'context': json.dumps(knowledge),
            'source_type': 'task',
            'confidence': self._calculate_confidence(knowledge),
            'metadata': json.dumps(metadata)
        })
        
        knowledge_store_logger.info("[KNOWLEDGE] JSON memory stored", extra={
            'agent_id': agent_id,
            'memory_id': memory_id,
            'memory_type': 'JSON',
            'metadata_size': len(json.dumps(metadata)),
            'confidence': self._calculate_confidence(knowledge)
        })
        
        return memory_id

    def _store_memory(self, agent_id: int, memory_type: str, 
                     knowledge: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Store memory in agent_memory table."""
        conn = None
        cursor = None
        try:
            knowledge_store_logger.info("[KNOWLEDGE] Starting memory storage", extra={
                'agent_id': agent_id,
                'memory_type': memory_type,
                'data_keys': list(data.keys()),
                'confidence': data['confidence']
            })
            
            # Ensure we have a valid connection
            self._ensure_db_connection()
            conn = self.db_conn
            
            if conn is None:
                raise Exception("Database connection is not available")
                
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO agent_memory (
                    agent_id, memory_type, start_prompt, end_prompt,
                    context, source_type, confidence, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, NOW()
                )
            """, (
                agent_id, memory_type, data['start_prompt'], data['end_prompt'],
                data['context'], data['source_type'], data['confidence']
            ))
            
            memory_id = cursor.lastrowid
            conn.commit()
            
            knowledge_store_logger.info("[KNOWLEDGE] Memory stored successfully", extra={
                'agent_id': agent_id,
                'memory_id': memory_id,
                'memory_type': memory_type,
                'context_size': len(data['context']),
                'confidence': data['confidence'],
                'timestamp': datetime.now().isoformat()
            })
            
            # Log LLM-related information
            knowledge_llm_logger.info("[LLM] Memory ready for LLM access", extra={
                'agent_id': agent_id,
                'memory_id': memory_id,
                'memory_type': memory_type,
                'prompt_length': len(data['start_prompt']) + len(data['end_prompt']),
                'context_size': len(data['context']),
                'confidence': data['confidence']
            })
            
            return memory_id
            
        except Exception as e:
            knowledge_store_logger.error("[KNOWLEDGE] Error storing memory", extra={
                'agent_id': agent_id,
                'memory_type': memory_type,
                'error': str(e),
                'error_type': type(e).__name__
            }, exc_info=True)
            raise
            
        finally:
            safe_close_connection(conn, cursor)

    def _identify_task_type(self, task: TeamTask) -> str:
        """Identify the type of task based on description and requirements."""
        desc = task.description.lower()
        
        knowledge_store_logger.debug("[KNOWLEDGE] Identifying task type", extra={
            'task_id': task.task_id,
            'description_length': len(desc),
            'has_requirements': bool(task.requirements)
        })
        
        task_type = 'general_task'
        if any(x in desc for x in ['predict', 'classify', 'train']):
            task_type = 'ml_task'
        elif any(x in desc for x in ['query', 'database', 'data']):
            task_type = 'data_task'
        elif any(x in desc for x in ['api', 'request', 'endpoint']):
            task_type = 'api_task'
        elif any(x in desc for x in ['compute', 'calculate', 'process']):
            task_type = 'computation_task'
        
        knowledge_store_logger.info("[KNOWLEDGE] Task type identified", extra={
            'task_id': task.task_id,
            'identified_type': task_type,
            'matched_keywords': [x for x in ['predict', 'classify', 'train', 'query', 'database', 'data', 'api', 'request', 'endpoint', 'compute', 'calculate', 'process']
                               if x in desc]
        })
        
        return task_type

    def _extract_success_patterns(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract success patterns from execution result."""
        patterns = []
        
        if result.get('status') == 'success':
            patterns.append({
                'type': 'execution_success',
                'tools': result.get('tools_used', []),
                'metrics': result.get('performance_metrics', {})
            })
            
        if result.get('validation_passed'):
            patterns.append({
                'type': 'validation_success',
                'validation_result': result.get('validation_result', {})
            })
            
        return patterns

    def _extract_error_patterns(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract error patterns from execution result."""
        patterns = []
        
        if result.get('status') == 'error':
            patterns.append({
                'type': 'execution_error',
                'error': result.get('error'),
                'context': result.get('error_context', {})
            })
            
        if not result.get('validation_passed'):
            patterns.append({
                'type': 'validation_error',
                'validation_result': result.get('validation_result', {})
            })
            
        return patterns

    def _calculate_confidence(self, knowledge: Dict[str, Any]) -> float:
        """Calculate confidence score for knowledge."""
        confidence = 0.5  # Base confidence
        
        # Adjust based on success patterns
        if knowledge.get('success_patterns'):
            confidence += 0.2
            
        # Adjust based on performance metrics
        metrics = knowledge.get('performance_metrics', {})
        if metrics.get('accuracy'):
            confidence += metrics['accuracy'] * 0.3
            
        # Cap confidence
        return min(confidence, 1.0)

    def store_predefined_knowledge(self, agent_id: int, knowledge_text: str, confidence: float = 1.0) -> Dict[str, Any]:
        """
        Store predefined knowledge for an agent.
        
        Args:
            agent_id: ID of the agent
            knowledge_text: The predefined knowledge text
            confidence: Confidence score for this knowledge (default: 1.0)
            
        Returns:
            Dictionary containing stored memory information
        """
        try:
            knowledge_store_logger.info("[KNOWLEDGE] Starting predefined knowledge storage", extra={
                'agent_id': agent_id,
                'knowledge_length': len(knowledge_text),
                'timestamp': datetime.now().isoformat()
            })
            
            # Create knowledge structure
            knowledge = {
                'task_type': 'predefined',
                'tools_used': [],
                'success_patterns': [knowledge_text],
                'error_patterns': [],
                'performance_metrics': {},
                'context': {
                    'task_description': 'Predefined agent knowledge',
                    'requirements': {},
                    'execution_time': 0,
                    'success_rate': 1.0
                }
            }
            
            # Store as long-term memory
            conn = None
            cursor = None
            try:
                conn = self.db_conn
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO agent_memory (
                        agent_id, memory_type, start_prompt, end_prompt,
                        context, source_type, confidence, created_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, NOW()
                    )
                """, (
                    agent_id,
                    'LONG_TERM_MEMORY',
                    knowledge_text,  # Use the knowledge text as start_prompt
                    knowledge_text,  # Use the knowledge text as end_prompt
                    json.dumps(knowledge),
                    'predefined',
                    confidence
                ))
                
                memory_id = cursor.lastrowid
                conn.commit()
                
                knowledge_store_logger.info("[KNOWLEDGE] Predefined knowledge stored successfully", extra={
                    'agent_id': agent_id,
                    'memory_id': memory_id,
                    'memory_type': 'LONG_TERM_MEMORY',
                    'confidence': confidence
                })
                
                return {
                    'status': 'success',
                    'memory_id': memory_id,
                    'message': 'Predefined knowledge stored successfully'
                }
                
            finally:
                safe_close_connection(conn, cursor)
            
        except Exception as e:
            knowledge_store_logger.error("[KNOWLEDGE] Error storing predefined knowledge", extra={
                'agent_id': agent_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'timestamp': datetime.now().isoformat()
            }, exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def _get_agent_memories(self, agent_id: int) -> List[Dict[str, Any]]:
        """Get agent's memories from the database."""
        try:
            cursor = self.db_conn.cursor(dictionary=True)
            
            # Get long-term memories
            cursor.execute("""
                SELECT 
                    id,
                    memory_type,
                    start_prompt,
                    end_prompt,
                    context,
                    confidence,
                    source_type,
                    created_at
                FROM agent_memory 
                WHERE agent_id = %s 
                AND memory_type = 'LONG_TERM_MEMORY'
                ORDER BY confidence DESC, created_at DESC
                LIMIT 10
            """, (agent_id,))
            
            memories = cursor.fetchall()
            
            # Process memories
            processed_memories = []
            for memory in memories:
                try:
                    # Parse context data
                    context_data = self._parse_and_validate_context(memory['context'], memory['id'])
                    
                    # Create memory object
                    processed_memory = {
                        'memory_id': memory['id'],
                        'memory_type': memory['memory_type'],
                        'source_type': memory['source_type'],
                        'content': {
                            'start_prompt': memory['start_prompt'] or '',
                            'end_prompt': memory['end_prompt'] or '',
                            'context': context_data,
                            'confidence': float(memory['confidence']) if memory['confidence'] else 0.0
                        },
                        'created_at': memory['created_at'].isoformat() if memory['created_at'] else None
                    }
                    
                    processed_memories.append(processed_memory)
                    
                except Exception as e:
                    workflow_logger.error(f"Error processing memory {memory.get('id')}: {str(e)}", exc_info=True)
                    continue
            
            return processed_memories
            
        except Exception as e:
            workflow_logger.error(f"Error getting agent memories: {str(e)}", exc_info=True)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()

    def _parse_and_validate_context(self, context: str, memory_id: int) -> Dict[str, Any]:
        """Parse and validate memory context data."""
        try:
            if not context:
                return {}
            
            # Try to parse JSON context
            try:
                context_data = json.loads(context)
                if not isinstance(context_data, dict):
                    raise ValueError("Context must be a dictionary")
                return context_data
            except json.JSONDecodeError:
                # If not JSON, return as plain text
                return {'text': context}
                
        except Exception as e:
            workflow_logger.error(f"Error parsing context for memory {memory_id}: {str(e)}", exc_info=True)
            return {}

    def _find_relevant_memories(self, memories: List[Dict[str, Any]], 
                              description: str,
                              requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find memories relevant to the task."""
        try:
            relevant_memories = []
            
            for memory in memories:
                # Calculate relevance score
                relevance_score = self._calculate_task_relevance(
                    description,
                    memory['content']['start_prompt'],
                    memory['content']['end_prompt']
                )
                
                # Add relevance score to memory
                memory['task_relevance'] = relevance_score
                
                # Only include memories with sufficient relevance
                if relevance_score >= 0.3:  # Minimum relevance threshold
                    relevant_memories.append(memory)
            
            # Sort by relevance
            relevant_memories.sort(key=lambda x: x['task_relevance'], reverse=True)
            
            return relevant_memories
            
        except Exception as e:
            workflow_logger.error(f"Error finding relevant memories: {str(e)}", exc_info=True)
            return []

    def _count_memory_sources(self, memories: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count memory sources."""
        try:
            source_counts = {}
            
            for memory in memories:
                source_type = memory.get('source_type', 'unknown')
                source_counts[source_type] = source_counts.get(source_type, 0) + 1
            
            return source_counts
            
        except Exception as e:
            workflow_logger.error(f"Error counting memory sources: {str(e)}", exc_info=True)
            return {}

    def _store_knowledge_retrieval(self, agent_id: int, task_id: Union[int, str],
                                 description: str, requirements: Dict[str, Any],
                                 memory_count: int, source_counts: Dict[str, int]) -> None:
        """Store knowledge retrieval metrics."""
        try:
            cursor = self.db_conn.cursor()
            
            # Check if task exists
            cursor.execute("""
                SELECT task_id FROM team_tasks WHERE task_id = %s
            """, (str(task_id),))
            
            if not cursor.fetchone():
                workflow_logger.warning(f"Task {task_id} not found in team_tasks table, skipping metrics storage")
                return
            
            # Store metrics if task exists
            cursor.execute("""
                INSERT INTO knowledge_retrieval_metrics (
                    agent_id,
                    task_id,
                    description,
                    requirements,
                    memory_count,
                    source_counts,
                    created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
            """, (
                agent_id,
                str(task_id),  # Convert task_id to string
                description,
                json.dumps(requirements),
                memory_count,
                json.dumps(source_counts)
            ))
            
            self.db_conn.commit()
            workflow_logger.info(f"Successfully stored knowledge retrieval metrics for task {task_id}")
            
        except Exception as e:
            workflow_logger.error(f"Error storing knowledge retrieval: {str(e)}", exc_info=True)
            if 'cursor' in locals():
                self.db_conn.rollback()
        finally:
            if 'cursor' in locals():
                cursor.close() 