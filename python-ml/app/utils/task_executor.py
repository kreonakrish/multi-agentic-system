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
        workflow_logger.info(f"[WORKFLOW] Correlation ID: {correlation_id}")
        workflow_logger.info("="*80 + "\n")
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Store team task
            workflow_logger.info("[WORKFLOW] Storing team task")
            task_data = {
                'description': task.description,
                'requirements': task.requirements,
                'task_type': task.task_type,
                'complexity': task.complexity,
                'priority': task.priority
            }
            task_id = store_team_task(cursor, team.team_id, task_data, correlation_id)
            workflow_logger.info(f"[WORKFLOW] Stored team task with ID: {task_id}")
            
            # Create workflow record
            workflow_logger.info("[WORKFLOW] Creating workflow record")
            workflow_id = create_workflow_record(cursor, team.team_id, task_id, correlation_id)
            workflow_logger.info(f"[WORKFLOW] Created workflow record with ID: {workflow_id}")
            
            # Get ordered list of team agents
            workflow_logger.info("[WORKFLOW] Getting ordered list of team agents")
            team_agents = get_team_agents_ordered(cursor, team.team_id)
            workflow_logger.info(f"[WORKFLOW] Retrieved {len(team_agents)} team agents")
            
            # Create workflow steps for agents
            workflow_logger.info("[WORKFLOW] Creating workflow steps")
            step_ids = create_workflow_steps(cursor, workflow_id, team_agents)
            workflow_logger.info(f"[WORKFLOW] Created {len(step_ids)} workflow steps")
            
            # Group agents by priority
            workflow_logger.info("[WORKFLOW] Grouping agents by priority")
            priority_groups = group_agents_by_priority(team_agents)
            sorted_priorities = sorted(priority_groups.keys(), reverse=True)
            workflow_logger.info(f"[WORKFLOW] Created {len(priority_groups)} priority groups")
            
            for priority in sorted_priorities:
                workflow_logger.info(f"[WORKFLOW] Priority {priority} group has {len(priority_groups[priority])} agents")
            
            # Initialize results tracking
            final_results = []
            successful_agents = 0
            
            # Execute agents in priority order
            for priority in sorted_priorities:
                qualified_agents = priority_groups[priority]
                workflow_logger.info(f"\n[WORKFLOW] Starting execution of priority {priority} group")
                workflow_logger.info(f"[WORKFLOW] {len(qualified_agents)} agents in this group")
                
                for agent_data in qualified_agents:
                    workflow_logger.info(f"\n[WORKFLOW] Processing agent {agent_data['agent_id']} ({agent_data['name']})")
                    workflow_logger.info(f"[WORKFLOW] Agent tools: {json.dumps(agent_data.get('tools', []), indent=2)}")
                    
                    try:
                        # Initialize agent
                        workflow_logger.info(f"[WORKFLOW] Initializing agent {agent_data['agent_id']}")
                        agent = initialize_agent_from_db(agent_data['agent_id'])
                        if not agent:
                            workflow_logger.error(f"[WORKFLOW] Could not initialize agent {agent_data['agent_id']}")
                            continue
                        
                        # Set correlation ID
                        agent.set_correlation_id(correlation_id)
                        workflow_logger.info(f"[WORKFLOW] Set correlation ID for agent {agent_data['agent_id']}")
                        
                        # Prepare message
                        workflow_logger.info(f"[WORKFLOW] Preparing execution message for agent {agent_data['agent_id']}")
                        message = {
                            "task_description": task.description,
                            "requirements": task.requirements,
                            "conversation_context": final_results,
                            "accuracy_threshold": float(agent_data['accuracy'] or 0.8),
                            "success_rate": float(agent_data['success'] or 0.9),
                            "priority": priority
                        }
                        
                        # Execute with agent
                        workflow_logger.info(f"[WORKFLOW] Executing agent {agent_data['agent_id']}")
                        result = agent.execute_with_tools(json.dumps(message))
                        workflow_logger.info(f"[WORKFLOW] Agent {agent_data['agent_id']} execution completed")
                        workflow_logger.info(f"[WORKFLOW] Execution status: {result.get('status', 'unknown')}")
                        
                        if result['status'] == 'success':
                            successful_agents += 1
                            workflow_logger.info(f"[WORKFLOW] Agent {agent_data['agent_id']} execution successful")
                        
                        # Add agent info to result
                        result.update({
                            'agent_id': agent_data['agent_id'],
                            'agent_name': agent_data['name'],
                            'priority': priority,
                            'step_order': len(final_results) + 1,
                            'accuracy': float(agent_data['accuracy'] or 0),
                            'success_rate': float(agent_data['success'] or 0)
                        })
                        
                        final_results.append(result)
                        workflow_logger.info(f"[WORKFLOW] Added result for agent {agent_data['agent_id']}")
                        
                    except Exception as e:
                        workflow_logger.error(f"[WORKFLOW] Error executing agent {agent_data['agent_id']}: {str(e)}", exc_info=True)
                        final_results.append({
                            'agent_id': agent_data['agent_id'],
                            'agent_name': agent_data['name'],
                            'status': 'error',
                            'message': str(e)
                        })
                
                workflow_logger.info(f"[WORKFLOW] Completed execution of priority {priority} group")
            
            # Update workflow steps status
            workflow_logger.info("[WORKFLOW] Updating workflow steps status")
            for result in final_results:
                # Map the status to allowed enum values
                raw_status = result.get('status', 'failed')
                if raw_status == 'success':
                    status = 'completed'
                elif raw_status == 'error':
                    status = 'failed'
                else:
                    status = 'failed'  # Default to failed for unknown statuses
                
                error_msg = result.get('message') if status == 'failed' else None
                update_workflow_steps_status(
                    cursor,
                    step_ids,  # Use the step_ids we got from create_workflow_steps
                    status,
                    error=error_msg,
                    result=result
                )
            workflow_logger.info("[WORKFLOW] Workflow steps status updated")
            
            # Update workflow status
            workflow_logger.info("[WORKFLOW] Updating workflow status")
            update_workflow_status(cursor, workflow_id, 'completed')
            workflow_logger.info("[WORKFLOW] Workflow status updated")
            
            # Aggregate results
            workflow_logger.info("[WORKFLOW] Aggregating team responses")
            aggregated = aggregate_team_responses(final_results, task.description)
            workflow_logger.info("[WORKFLOW] Team responses aggregated")
            
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
            workflow_logger.error(f"[WORKFLOW] Error in task execution: {str(e)}", exc_info=True)
            if workflow_id:
                workflow_logger.info("[WORKFLOW] Updating workflow status to failed")
                update_workflow_status(cursor, workflow_id, 'failed')
                workflow_logger.info("[WORKFLOW] Workflow status updated")
            return {
                'status': 'error',
                'message': str(e),
                'workflow_id': workflow_id
            }
            
        finally:
            safe_close_connection(conn, cursor)
            
    except Exception as e:
        workflow_logger.error(f"[WORKFLOW] Critical error in task execution: {str(e)}", exc_info=True)
        return {
            'status': 'error',
            'message': str(e),
            'workflow_id': None
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