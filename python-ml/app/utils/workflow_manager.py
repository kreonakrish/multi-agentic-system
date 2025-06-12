"""Workflow manager for orchestrating task execution with enhanced capabilities."""
from typing import Dict, Any, List, Optional
import json
import uuid
import logging
from datetime import datetime
from app.models.team import Team, TeamTask
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.context_analyzer import ContextAnalyzer
from app.utils.task_decomposer import TaskDecomposer
from app.utils.knowledge_manager import KnowledgeManager
from app.utils.agent_coordinator import AgentCoordinator
from app.utils.json_encoder import CustomJSONEncoder
from app.services.agent_service import initialize_agent_from_db
from app.utils.team_utils import (
    store_team_task,
    create_workflow_record,
    get_team_agents_ordered,
    group_agents_by_priority,
    create_workflow_steps,
    aggregate_team_responses
)

# Get workflow-specific loggers
workflow_logger = logging.getLogger('multi_agent_system.workflow')
workflow_steps_logger = logging.getLogger('multi_agent_system.workflow.steps')
workflow_execution_logger = logging.getLogger('multi_agent_system.workflow.execution')
workflow_decision_logger = logging.getLogger('multi_agent_system.workflow.decisions')

class WorkflowManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.context_analyzer = ContextAnalyzer()
        self.task_decomposer = TaskDecomposer()
        self.knowledge_manager = KnowledgeManager()
        self.agent_coordinator = AgentCoordinator()

    def execute_workflow(self, team: Team, task: TeamTask) -> Dict[str, Any]:
        """Execute a workflow with enhanced task decomposition and knowledge management."""
        try:
            workflow_id = None
            workflow_start_time = datetime.now()
            correlation_id = str(uuid.uuid4())
            
            self._log_workflow_start(task, team)
            workflow_logger.info(f"[WORKFLOW] Generated correlation ID: {correlation_id}", extra={
                'task_id': task.task_id,
                'team_id': team.team_id,
                'task_type': task.task_type,
                'correlation_id': correlation_id
            })
            
            # Log smart workflow decision
            workflow_decision_logger.info("[DECISION] Smart workflow execution initiated", extra={
                'correlation_id': correlation_id,
                'team_id': team.team_id,
                'task_id': task.task_id,
                'task_type': task.task_type,
                'task_priority': task.priority,
                'task_complexity': task.complexity,
                'team_size': len(team.members) if team.members else 0,
                'execution_mode': 'smart_workflow'
            })
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            try:
                result = self._execute_enhanced_workflow(
                    cursor, team, task, correlation_id
                )
                
                workflow_logger.info("[WORKFLOW] Enhanced workflow execution completed")
                workflow_logger.info(f"[WORKFLOW] Final status: {result.get('final_status', 'unknown')}")
                workflow_logger.info(f"[WORKFLOW] Successful agents: {result.get('successful_agents', 0)}")
                
                # Log workflow completion metrics
                workflow_decision_logger.info("[DECISION] Workflow execution completed", extra={
                    'correlation_id': correlation_id,
                    'workflow_id': result.get('workflow_id'),
                    'execution_time': (datetime.now() - workflow_start_time).total_seconds(),
                    'successful_agents': result.get('successful_agents', 0),
                    'total_agents': len(result.get('team_agents', [])),
                    'final_status': result.get('final_status', 'unknown'),
                    'context_analysis_success': bool(result.get('context_analysis')),
                    'decomposition_success': bool(result.get('decomposition')),
                    'error_count': len([r for r in result.get('results', []) if r.get('status') == 'error'])
                })
                
                result['execution_summary'] = {
                    'context_analysis': result.get('context_analysis', {}),
                    'decomposition': result.get('decomposition', {}),
                    'workflow_id': result.get('workflow_id'),
                    'successful_agents': result.get('successful_agents', 0),
                    'total_agents': len(result.get('team_agents', [])),
                    'execution_time': (datetime.now() - workflow_start_time).total_seconds()
                }
                
                return result
                
            except Exception as e:
                return self._handle_execution_error(e, workflow_id, workflow_start_time)
                
            finally:
                safe_close_connection(conn, cursor)
                
        except Exception as e:
            return self._handle_critical_error(e, workflow_start_time)

    def _execute_enhanced_workflow(self, cursor, team: Team, task: TeamTask, 
                                 correlation_id: str) -> Dict[str, Any]:
        """Execute workflow with enhanced features while maintaining compatibility."""
        try:
            workflow_logger.info("[WORKFLOW] Starting enhanced workflow execution")
            
            # Store team task
            task_data = {
                'description': task.description,
                'requirements': task.requirements
            }
            task_id = store_team_task(cursor, team.team_id, task_data, correlation_id)
            workflow_logger.info(f"[WORKFLOW] Stored team task with ID: {task_id}")
            
            # Create workflow record
            workflow_id = create_workflow_record(cursor, team.team_id, task_id, correlation_id)
            workflow_logger.info(f"[WORKFLOW] Created workflow record with ID: {workflow_id}")
            
            # Enhanced: Analyze context
            workflow_logger.info("[WORKFLOW] Starting context analysis")
            context_analysis = self.context_analyzer.analyze(task, team)
            workflow_logger.info("[WORKFLOW] Context analysis completed")
            workflow_logger.info(f"[WORKFLOW] Required tools: {json.dumps(context_analysis.get('required_tools', []), indent=2)}")
            workflow_logger.info(f"[WORKFLOW] Dependencies: {json.dumps(context_analysis.get('dependencies', []), indent=2)}")
            
            # Log context analysis decisions
            workflow_decision_logger.info("[DECISION] Context analysis completed", extra={
                'correlation_id': correlation_id,
                'workflow_id': workflow_id,
                'required_tools': context_analysis.get('required_tools', []),
                'dependencies': context_analysis.get('dependencies', []),
                'complexity_score': context_analysis.get('complexity_score', 0),
                'confidence_score': context_analysis.get('confidence_score', 0),
                'tool_compatibility': context_analysis.get('tool_compatibility', {}),
                'agent_requirements': context_analysis.get('agent_requirements', [])
            })
            
            # Enhanced: Decompose task
            workflow_logger.info("[WORKFLOW] Starting task decomposition")
            decomposition = self.task_decomposer.decompose(task, context_analysis)
            workflow_logger.info(f"[WORKFLOW] Task decomposed into {len(decomposition.get('subtasks', []))} subtasks")
            
            # Log task decomposition decisions
            workflow_decision_logger.info("[DECISION] Task decomposition completed", extra={
                'correlation_id': correlation_id,
                'workflow_id': workflow_id,
                'subtask_count': len(decomposition.get('subtasks', [])),
                'decomposition_strategy': decomposition.get('strategy'),
                'critical_path_length': decomposition.get('critical_path_length'),
                'parallel_execution_groups': decomposition.get('parallel_groups', []),
                'dependencies_graph': decomposition.get('dependencies_graph', {})
            })
            
            # Get team agents
            workflow_logger.info("[WORKFLOW] Retrieving team agents")
            team_agents = get_team_agents_ordered(cursor, team.team_id)
            workflow_logger.info(f"[WORKFLOW] Retrieved {len(team_agents)} team agents")
            
            # Log agent selection decisions
            workflow_decision_logger.info("[DECISION] Team agents retrieved", extra={
                'correlation_id': correlation_id,
                'workflow_id': workflow_id,
                'total_agents': len(team_agents),
                'agent_capabilities': {
                    agent['agent_id']: {
                        'tools': agent.get('tools', []),
                        'accuracy': agent.get('accuracy'),
                        'success_rate': agent.get('success'),
                        'priority': agent.get('priority')
                    } for agent in team_agents
                }
            })
            
            # Enhanced: Get agent assignments
            workflow_logger.info("[WORKFLOW] Starting agent task assignment")
            assignments = self.agent_coordinator.assign_tasks(team, task, decomposition)
            workflow_logger.info(f"[WORKFLOW] Created {len(assignments)} agent assignments")
            
            # Log assignment decisions
            workflow_decision_logger.info("[DECISION] Agent task assignments created", extra={
                'correlation_id': correlation_id,
                'workflow_id': workflow_id,
                'assignment_count': len(assignments),
                'assignments': {
                    agent_id: {
                        'subtasks': subtasks,
                        'priority': next((a['priority'] for a in team_agents if a['agent_id'] == agent_id), None),
                        'tools_required': next((a.get('tools', []) for a in team_agents if a['agent_id'] == agent_id), [])
                    } for agent_id, subtasks in assignments.items()
                }
            })
            
            # Create workflow steps
            workflow_logger.info("[WORKFLOW] Creating workflow steps")
            step_ids = self._create_enhanced_workflow_steps(
                cursor, workflow_id, team_agents, assignments
            )
            workflow_logger.info(f"[WORKFLOW] Created {len(step_ids)} workflow steps")
            
            # Group agents by priority
            workflow_logger.info("[WORKFLOW] Grouping agents by priority")
            priority_groups = group_agents_by_priority(team_agents)
            sorted_priorities = sorted(priority_groups.keys(), reverse=True)
            workflow_logger.info(f"[WORKFLOW] Created {len(priority_groups)} priority groups")
            
            # Log priority grouping decisions
            workflow_decision_logger.info("[DECISION] Agent priority groups created", extra={
                'correlation_id': correlation_id,
                'workflow_id': workflow_id,
                'priority_group_count': len(priority_groups),
                'priority_distribution': {
                    priority: len(agents) for priority, agents in priority_groups.items()
                },
                'execution_order': sorted_priorities
            })
            
            for priority in sorted_priorities:
                workflow_logger.info(f"[WORKFLOW] Priority {priority} group has {len(priority_groups[priority])} agents")
            
            # Execute agents with enhanced knowledge integration
            workflow_logger.info("[WORKFLOW] Starting agent execution with knowledge integration")
            execution_results = self._execute_agents_with_knowledge(
                priority_groups,
                sorted_priorities,
                task,
                correlation_id,
                context_analysis
            )
            workflow_logger.info("[WORKFLOW] Agent execution completed")
            workflow_logger.info(f"[WORKFLOW] Successful agents: {execution_results['successful_agents']}")
            
            # Log execution results
            workflow_decision_logger.info("[DECISION] Agent execution completed", extra={
                'correlation_id': correlation_id,
                'workflow_id': workflow_id,
                'successful_agents': execution_results['successful_agents'],
                'execution_results': {
                    result['agent_id']: {
                        'status': result.get('status'),
                        'confidence': result.get('confidence'),
                        'execution_time': result.get('execution_time'),
                        'error': result.get('error'),
                        'tool_usage': result.get('tool_usage', []),
                        'llm_communication_success': result.get('llm_communication_success', False)
                    } for result in execution_results['results']
                }
            })
            
            # Update workflow status
            workflow_logger.info("[WORKFLOW] Updating workflow status")
            cursor.execute("""
                UPDATE workflows
                SET status = %s,
                    end_time = NOW()
                WHERE id = %s
            """, (
                'completed' if execution_results['successful_agents'] > 0 else 'failed',
                workflow_id
            ))
            workflow_logger.info("[WORKFLOW] Workflow status updated")
            
            return {
                'workflow_id': workflow_id,
                'task_id': task_id,
                'final_status': 'completed' if execution_results['successful_agents'] > 0 else 'failed',
                'results': execution_results['results'],
                'context_analysis': context_analysis,
                'decomposition': decomposition,
                'team_agents': team_agents,
                'successful_agents': execution_results['successful_agents']
            }
            
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Error in team execution: {str(e)}", exc_info=True)
            workflow_logger.warning("[WORKFLOW] Rolling back uncommitted transaction")
            cursor.execute("ROLLBACK")
            return {
                'workflow_id': workflow_id if 'workflow_id' in locals() else None,
                'task_id': task_id if 'task_id' in locals() else None,
                'final_status': 'failed',
                'error': str(e)
            }

    def _execute_agents_with_knowledge(self, priority_groups: Dict[int, List[Dict[str, Any]]], 
                                     sorted_priorities: List[int], task: TeamTask,
                                     correlation_id: str, 
                                     context_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agents with enhanced knowledge integration."""
        final_results = []
        successful_agents = 0
        
        for priority in sorted_priorities:
            qualified_agents = priority_groups[priority]
            workflow_logger.info(f"[WORKFLOW] Starting execution of priority {priority} group")
            workflow_logger.info(f"[WORKFLOW] {len(qualified_agents)} agents in this priority group")
            
            # Log priority group execution start
            workflow_decision_logger.info("[DECISION] Starting priority group execution", extra={
                'correlation_id': correlation_id,
                'priority_level': priority,
                'agent_count': len(qualified_agents),
                'agents': [
                    {
                        'agent_id': agent['agent_id'],
                        'name': agent['name'],
                        'tools': agent.get('tools', []),
                        'accuracy': agent.get('accuracy'),
                        'success_rate': agent.get('success')
                    } for agent in qualified_agents
                ]
            })
            
            for agent_data in qualified_agents:
                workflow_logger.info(f"[WORKFLOW] Processing agent {agent_data['agent_id']} ({agent_data['name']})")
                workflow_logger.info(f"[WORKFLOW] Agent tools: {json.dumps(agent_data.get('tools', []), indent=2)}")
                
                # Log agent execution start
                workflow_decision_logger.info("[DECISION] Starting agent execution", extra={
                    'correlation_id': correlation_id,
                    'agent_id': agent_data['agent_id'],
                    'agent_name': agent_data['name'],
                    'priority': priority,
                    'tools': agent_data.get('tools', []),
                    'accuracy_threshold': float(agent_data.get('accuracy') or 0.8),
                    'success_rate': float(agent_data.get('success') or 0.9),
                    'required_tools': context_analysis.get('required_tools', []),
                    'tool_compatibility': any(
                        tool['tool_id'] in agent_data.get('tools', [])
                        for tool in context_analysis.get('required_tools', [])
                    )
                })
                
                try:
                    # Initialize agent
                    workflow_logger.info(f"[WORKFLOW] Initializing agent {agent_data['agent_id']}")
                    agent = initialize_agent_from_db(agent_data['agent_id'])
                    if not agent:
                        workflow_logger.error(f"[WORKFLOW] Could not initialize agent {agent_data['agent_id']}")
                        workflow_decision_logger.error("[DECISION] Agent initialization failed", extra={
                            'correlation_id': correlation_id,
                            'agent_id': agent_data['agent_id'],
                            'reason': 'initialization_failed'
                        })
                        continue
                    
                    # Set correlation ID
                    agent.set_correlation_id(correlation_id)
                    workflow_logger.info(f"[WORKFLOW] Set correlation ID for agent {agent_data['agent_id']}")
                    
                    # Get relevant knowledge
                    workflow_logger.info(f"[WORKFLOW] Retrieving knowledge for agent {agent_data['agent_id']}")
                    knowledge = self.knowledge_manager.get_relevant_knowledge(
                        agent_data['agent_id'],
                        task
                    )
                    workflow_logger.info(f"[WORKFLOW] Retrieved {len(knowledge) if knowledge else 0} knowledge items")
                    
                    # Log knowledge retrieval
                    # Extract memories from knowledge result
                    memories = knowledge.get('memories', {})
                    long_term_memories = memories.get('long_term', [])
                    short_term_memories = memories.get('short_term', [])
                    graph_memories = memories.get('graph', [])
                    json_memories = memories.get('json', [])
                    
                    # Log knowledge retrieval
                    workflow_decision_logger.info("[DECISION] Agent knowledge retrieved", extra={
                        'correlation_id': correlation_id,
                        'agent_id': agent_data['agent_id'],
                        'knowledge_items_count': sum(len(m) for m in [long_term_memories, short_term_memories, graph_memories, json_memories]),
                        'knowledge_types': list(set(m['memory_type'] for m in long_term_memories))
                    })
                    
                    # Prepare enhanced message
                    workflow_logger.info(f"[WORKFLOW] Preparing execution message for agent {agent_data['agent_id']}")
                    message = {
                        "task_description": task.description,
                        "requirements": task.requirements,
                        "conversation_context": final_results,
                        "accuracy_threshold": float(agent_data['accuracy'] or 0.8),
                        "success_rate": float(agent_data['success'] or 0.9),
                        "priority": priority,
                        "knowledge_context": {
                            'long_term': long_term_memories,
                            'short_term': short_term_memories,
                            'graph': graph_memories,
                            'json': json_memories
                        },
                        "context_analysis": context_analysis
                    }
                    
                    # Execute with agent
                    workflow_logger.info(f"[WORKFLOW] Executing agent {agent_data['agent_id']}")
                    execution_start_time = datetime.now()
                    result = agent.execute_with_tools(json.dumps(message, cls=CustomJSONEncoder))
                    execution_time = (datetime.now() - execution_start_time).total_seconds()
                    
                    workflow_logger.info(f"[WORKFLOW] Agent {agent_data['agent_id']} execution completed")
                    workflow_logger.info(f"[WORKFLOW] Execution status: {result.get('status', 'unknown')}")
                    
                    # Log execution completion
                    workflow_decision_logger.info("[DECISION] Agent execution completed", extra={
                        'correlation_id': correlation_id,
                        'agent_id': agent_data['agent_id'],
                        'execution_time': execution_time,
                        'status': result.get('status'),
                        'confidence': result.get('confidence'),
                        'tool_usage': result.get('tool_usage', []),
                        'llm_communication_success': result.get('llm_communication_success', False),
                        'error': result.get('error') if result.get('status') == 'error' else None
                    })
                    
                    if result['status'] == 'success':
                        successful_agents += 1
                        workflow_logger.info(f"[WORKFLOW] Agent {agent_data['agent_id']} execution successful")
                        
                        # Store new knowledge
                        workflow_logger.info(f"[WORKFLOW] Storing new knowledge from agent {agent_data['agent_id']}")
                        self.knowledge_manager.store_task_knowledge(
                            agent_data['agent_id'],
                            task,
                            result
                        )
                        workflow_logger.info(f"[WORKFLOW] Knowledge stored for agent {agent_data['agent_id']}")
                        
                        # Log knowledge storage
                        workflow_decision_logger.info("[DECISION] New knowledge stored", extra={
                            'correlation_id': correlation_id,
                            'agent_id': agent_data['agent_id'],
                            'knowledge_type': result.get('knowledge_type'),
                            'knowledge_tags': result.get('knowledge_tags', [])
                        })
                    
                    # Add agent info to result
                    result.update({
                        'agent_id': agent_data['agent_id'],
                        'agent_name': agent_data['name'],
                        'priority': priority,
                        'step_order': len(final_results) + 1,
                        'accuracy': float(agent_data['accuracy'] or 0),
                        'success_rate': float(agent_data['success'] or 0),
                        'execution_time': execution_time
                    })
                    
                    final_results.append(result)
                    workflow_logger.info(f"[WORKFLOW] Added result for agent {agent_data['agent_id']}")
                    
                except Exception as e:
                    workflow_logger.error(f"[WORKFLOW] Error executing agent {agent_data['agent_id']}: {str(e)}", exc_info=True)
                    workflow_decision_logger.error("[DECISION] Agent execution error", extra={
                        'correlation_id': correlation_id,
                        'agent_id': agent_data['agent_id'],
                        'error': str(e),
                        'error_type': type(e).__name__
                    })
                    final_results.append({
                        'agent_id': agent_data['agent_id'],
                        'agent_name': agent_data['name'],
                        'status': 'error',
                        'message': str(e)
                    })
            
            workflow_logger.info(f"[WORKFLOW] Completed execution of priority {priority} group")
            
            # Log priority group completion
            workflow_decision_logger.info("[DECISION] Priority group execution completed", extra={
                'correlation_id': correlation_id,
                'priority_level': priority,
                'successful_agents_in_group': len([
                    r for r in final_results 
                    if r.get('priority') == priority and r.get('status') == 'success'
                ]),
                'total_agents_in_group': len(qualified_agents)
            })
        
        workflow_logger.info("[WORKFLOW] All agent executions completed")
        workflow_logger.info(f"[WORKFLOW] Total successful agents: {successful_agents}")
        
        return {
            'results': final_results,
            'successful_agents': successful_agents
        }

    def _create_enhanced_workflow_steps(self, cursor, workflow_id: int, 
                                      team_agents: List[Dict[str, Any]],
                                      assignments: Dict[str, Any]) -> List[int]:
        """Create workflow steps with enhanced task assignments."""
        workflow_logger.info(f"[WORKFLOW] Creating enhanced workflow steps for {len(team_agents)} agents")
        step_ids = []
        
        # First, update the workflow's task_data to include assignments
        cursor.execute("""
            UPDATE workflows 
            SET task_data = JSON_SET(
                COALESCE(task_data, '{}'),
                '$.assignments',
                %s
            )
            WHERE id = %s
        """, (json.dumps(assignments), workflow_id))
        
        for idx, agent_data in enumerate(team_agents):
            agent_assignments = assignments.get(str(agent_data['agent_id']), [])
            workflow_logger.info(f"[WORKFLOW] Creating step for agent {agent_data['agent_id']}")
            workflow_logger.info(f"[WORKFLOW] Agent has {len(agent_assignments)} task assignments")
            
            cursor.execute("""
                INSERT INTO workflow_steps (
                    workflow_id, agent_id, step_order, status, 
                    start_time, tool_input
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                workflow_id,
                agent_data['agent_id'],
                idx + 1,
                'pending',
                datetime.now(),
                json.dumps(agent_assignments)  # Store assignments in tool_input for reference
            ))
            step_id = cursor.lastrowid
            step_ids.append(step_id)
            workflow_logger.info(f"[WORKFLOW] Created step {step_id} for agent {agent_data['agent_id']}")
        
        workflow_logger.info(f"[WORKFLOW] Created {len(step_ids)} workflow steps")
        return step_ids

    def _log_workflow_start(self, task: TeamTask, team: Team) -> None:
        """Log workflow start information."""
        workflow_logger.info("\n" + "="*80, extra={
            'task_id': task.task_id,
            'team_id': team.team_id,
            'task_type': task.task_type,
            'correlation_id': '-'
        })
        workflow_logger.info("[WORKFLOW] Starting new workflow execution", extra={
            'task_id': task.task_id,
            'team_id': team.team_id,
            'task_type': task.task_type,
            'correlation_id': '-'
        })
        workflow_logger.info(f"[WORKFLOW] Task ID: {task.task_id}", extra={
            'task_id': task.task_id,
            'team_id': team.team_id,
            'task_type': task.task_type,
            'correlation_id': '-'
        })
        workflow_logger.info(f"[WORKFLOW] Team ID: {team.team_id}", extra={
            'task_id': task.task_id,
            'team_id': team.team_id,
            'task_type': task.task_type,
            'correlation_id': '-'
        })
        workflow_logger.info(f"[WORKFLOW] Description: {task.description}", extra={
            'task_id': task.task_id,
            'team_id': team.team_id,
            'task_type': task.task_type,
            'correlation_id': '-'
        })
        workflow_logger.info("="*80 + "\n", extra={
            'task_id': task.task_id,
            'team_id': team.team_id,
            'task_type': task.task_type,
            'correlation_id': '-'
        })

    def _log_workflow_completion(self, workflow_start_time: datetime, 
                               successful_agents: int, total_agents: int) -> None:
        """Log workflow completion information."""
        workflow_logger.info("\n" + "="*80)
        workflow_logger.info("[WORKFLOW] Task execution completed")
        workflow_logger.info(f"[WORKFLOW] Final Status: COMPLETED")
        workflow_logger.info(
            f"[WORKFLOW] Execution Time: {(datetime.now() - workflow_start_time).total_seconds():.2f} seconds"
        )
        workflow_logger.info(f"[WORKFLOW] Successful Agents: {successful_agents}/{total_agents}")
        workflow_logger.info(f"[WORKFLOW] End Time: {datetime.now().isoformat()}")
        workflow_logger.info("="*80 + "\n")

    def _handle_execution_error(self, error: Exception, workflow_id: Optional[int], 
                              workflow_start_time: datetime) -> Dict[str, Any]:
        """Handle workflow execution errors."""
        workflow_logger.error(f"[WORKFLOW] Error in team execution: {str(error)}", exc_info=True)
        return {
            'workflow_id': workflow_id,
            'final_status': 'failed',
            'error': str(error),
            'results': [],
            'aggregated_data': {
                'vector_store': {'results': [], 'queries': [], 'datasets': []},
                'raw_data': {'samples': [], 'total_records': 0, 'schemas': []},
                'tool_results': [],
                'llm_responses': []
            },
            'execution_summary': {
                'total_agents': 0,
                'successful_agents': 0,
                'priority_groups': [],
                'execution_time': (datetime.now() - workflow_start_time).total_seconds()
            }
        }

    def _handle_critical_error(self, error: Exception, 
                             workflow_start_time: datetime) -> Dict[str, Any]:
        """Handle critical workflow errors."""
        workflow_logger.error(f"[WORKFLOW] Critical error in team execution: {str(error)}", exc_info=True)
        return {
            'workflow_id': None,
            'final_status': 'failed',
            'error': str(error),
            'results': [],
            'aggregated_data': {
                'vector_store': {'results': [], 'queries': [], 'datasets': []},
                'raw_data': {'samples': [], 'total_records': 0, 'schemas': []},
                'tool_results': [],
                'llm_responses': []
            },
            'execution_summary': {
                'total_agents': 0,
                'successful_agents': 0,
                'priority_groups': [],
                'execution_time': (datetime.now() - workflow_start_time).total_seconds()
            }
        } 