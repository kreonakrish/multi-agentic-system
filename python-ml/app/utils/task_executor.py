from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.team import Team, TeamTask
from app.services.agent_service import initialize_agent_from_db
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.logger import logger
from app.utils.team_utils import (
    store_team_task,
    create_workflow_record,
    get_team_agents_ordered,
    group_agents_by_priority,
    create_workflow_steps,
    execute_priority_group,
    update_workflow_steps_status,
    update_workflow_status,
    aggregate_team_responses
)
from datetime import datetime
import json
import uuid
import logging

# Get workflow-specific loggers
workflow_logger = logging.getLogger('multi_agent_system.workflow')
workflow_steps_logger = logging.getLogger('multi_agent_system.workflow.steps')
workflow_execution_logger = logging.getLogger('multi_agent_system.workflow.execution')

def execute_task_with_team(team: Team, task: TeamTask) -> Dict[str, Any]:
    """Execute a task using a team of agents with proper coordination"""
    try:
        # Initialize workflow tracking
        workflow_id = None
        workflow_start_time = datetime.now()
        correlation_id = str(uuid.uuid4())
        
        workflow_logger.info("\n" + "="*80)
        workflow_logger.info("[WORKFLOW] Starting new workflow execution")
        workflow_logger.info(f"[WORKFLOW] Task ID: {task.task_id}")
        workflow_logger.info(f"[WORKFLOW] Team ID: {team.team_id}")
        workflow_logger.info(f"[WORKFLOW] Description: {task.description}")
        workflow_logger.info("="*80 + "\n")
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Store team task
            task_data = {
                'description': task.description,
                'requirements': task.requirements
            }
            task_id = store_team_task(cursor, team.team_id, task_data, correlation_id)
            
            # Create workflow record
            workflow_id = create_workflow_record(cursor, team.team_id, task_id, correlation_id)
            
            # Get ordered list of team agents
            team_agents = get_team_agents_ordered(cursor, team.team_id)
            
            # Create workflow steps for agents
            step_ids = create_workflow_steps(cursor, workflow_id, team_agents)
            
            # Group agents by priority
            priority_groups = group_agents_by_priority(team_agents)
            sorted_priorities = sorted(priority_groups.keys(), reverse=True)
            
            # Initialize results tracking
            final_results = []
            successful_agents = 0
            
            # Execute agents in priority order
            for priority in sorted_priorities:
                qualified_agents = priority_groups[priority]
                workflow_logger.info(f"[WORKFLOW] Executing priority {priority} group with {len(qualified_agents)} agents")
                
                # Execute each agent in the current priority group
                for agent_data in qualified_agents:
                    try:
                        # Initialize agent
                        agent = initialize_agent_from_db(agent_data['agent_id'])
                        if not agent:
                            workflow_logger.error(f"Could not initialize agent {agent_data['agent_id']}")
                            continue
                        
                        # Set correlation ID for tracking
                        agent.set_correlation_id(correlation_id)
                        
                        # Prepare message with context and requirements
                        message = {
                            "task_description": task.description,
                            "requirements": task.requirements,
                            "conversation_context": final_results,
                            "accuracy_threshold": agent_data['accuracy'] or 0.8,
                            "success_rate": agent_data['success'] or 0.9,
                            "priority": priority
                        }
                        
                        # Execute with agent
                        result = agent.execute_with_tools(json.dumps(message))
                        
                        if result['status'] == 'success':
                            successful_agents += 1
                            
                        # Add agent info to result
                        result.update({
                            'agent_id': agent_data['agent_id'],
                            'agent_name': agent_data['name'],
                            'priority': priority,
                            'step_order': len(final_results) + 1,
                            'accuracy': agent_data['accuracy'],
                            'success_rate': agent_data['success']
                        })
                        
                        final_results.append(result)
                        
                    except Exception as e:
                        workflow_logger.error(f"Error executing agent {agent_data['agent_id']}: {str(e)}")
                        final_results.append({
                            'agent_id': agent_data['agent_id'],
                            'agent_name': agent_data['name'],
                            'status': 'error',
                            'message': str(e)
                        })
            
            # Aggregate results
            aggregated = aggregate_team_responses(final_results, task.description)
            
            # Update workflow record with completion
            cursor.execute("""
                UPDATE workflows 
                SET status = %s, end_time = %s, execution_time = %s, 
                    successful_agents = %s, total_agents = %s
                WHERE id = %s
            """, (
                'completed',
                datetime.now(),
                (datetime.now() - workflow_start_time).total_seconds(),
                successful_agents,
                len(team_agents),
                workflow_id
            ))
            conn.commit()
            
            workflow_logger.info("\n" + "="*80)
            workflow_logger.info("[WORKFLOW] Task execution completed")
            workflow_logger.info(f"[WORKFLOW] Final Status: COMPLETED")
            workflow_logger.info(f"[WORKFLOW] Execution Time: {(datetime.now() - workflow_start_time).total_seconds():.2f} seconds")
            workflow_logger.info(f"[WORKFLOW] Successful Agents: {successful_agents}/{len(team_agents)}")
            workflow_logger.info(f"[WORKFLOW] End Time: {datetime.now().isoformat()}")
            workflow_logger.info("="*80 + "\n")
            
            return {
                'workflow_id': workflow_id,
                'final_status': 'completed',
                'results': final_results,
                'aggregated_data': aggregated['aggregated_data'],
                'validation_result': aggregated['validation_result'],
                'validation_passed': aggregated['validation_passed'],
                'execution_summary': {
                    'total_agents': len(team_agents),
                    'successful_agents': successful_agents,
                    'priority_groups': sorted_priorities,
                    'execution_time': (datetime.now() - workflow_start_time).total_seconds()
                }
            }
            
        except Exception as e:
            workflow_logger.error(f"[WORKFLOW] Error in team execution: {str(e)}", exc_info=True)
            return {
                'workflow_id': workflow_id,
                'final_status': 'failed',
                'error': str(e),
                'results': final_results if 'final_results' in locals() else [],
                'aggregated_data': {
                    'vector_store': {
                        'results': [],
                        'queries': [],
                        'datasets': []
                    },
                    'raw_data': {
                        'samples': [],
                        'total_records': 0,
                        'schemas': []
                    },
                    'tool_results': [],
                    'llm_responses': []
                },
                'execution_summary': {
                    'total_agents': len(team_agents) if 'team_agents' in locals() else 0,
                    'successful_agents': successful_agents if 'successful_agents' in locals() else 0,
                    'priority_groups': sorted(priority_groups.keys(), reverse=True) if 'priority_groups' in locals() else [],
                    'execution_time': (datetime.now() - workflow_start_time).total_seconds()
                }
            }
            
        finally:
            safe_close_connection(conn, cursor)
            
    except Exception as e:
        workflow_logger.error(f"[WORKFLOW] Critical error in team execution: {str(e)}", exc_info=True)
        return {
            'workflow_id': workflow_id if 'workflow_id' in locals() else None,
            'final_status': 'failed',
            'error': str(e),
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

def execute_agent_task(agent: Any, task: TeamTask, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a task with a single agent.
    Args:
        agent: The agent to execute the task
        task: The task to execute
        context: The execution context
    Returns:
        Dictionary containing agent's execution results
    """
    try:
        # Get OpenAI client from agent
        openai = agent.get_openai_client()
        
        # Prepare system message based on agent's role and tools
        tools_desc = "\n".join([f"- {t.name}: {t.description}" for t in agent.tools])
        system_message = f"""You are {agent.name}, an AI agent with the following tools:
{tools_desc}

Your task is to help users by providing accurate and helpful responses.
Use your tools when appropriate to enhance your responses.
"""
        
        # Get conversation history from context
        history = task.requirements.get('context', {}).get('conversation_history', [])
        
        # Build messages array with valid roles
        messages = [{"role": "system", "content": system_message}]
        
        # Add conversation history with valid roles
        for msg in history:
            # Map custom roles to OpenAI roles
            role = {
                'user': 'user',
                'agent': 'assistant',
                'tool': 'function',
                'bot': 'assistant'
            }.get(msg['role'], 'user')  # Default to user if unknown role
            
            messages.append({
                "role": role,
                "content": msg['content']
            })
        
        # Add the current task
        messages.append({
            "role": "user",
            "content": task.description
        })
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model=agent.foundation_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extract LLM response
        llm_response = response.choices[0].message.content
        
        return {
            'status': 'success',
            'message': f"Agent {agent.name} processed task {task.task_id}",
            'llm_response': llm_response,
            'context': context
        }
    except Exception as e:
        logger.error(f"Agent task execution failed: {str(e)}")
        raise 