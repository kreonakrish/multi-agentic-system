"""Utility functions for team task execution"""
from typing import Dict, List, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import uuid
from app.utils.logger import logger
from app.services.agent_service import initialize_agent_from_db

def store_team_task(cursor, team_id: int, task_data: Dict[str, Any], correlation_id: str) -> int:
    """Store team task in database and return task_id"""
    task_id = str(uuid.uuid4())  # Generate a unique task ID
    cursor.execute("""
        INSERT INTO team_messages (
            team_id,
            task_id,
            task_description,
            task_requirements,
            team_config,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        team_id,
        task_id,
        task_data.get('description', ''),
        json.dumps(task_data.get('requirements', {})),
        json.dumps({'correlation_id': correlation_id}),
        'pending',
        datetime.now(),
        datetime.now()
    ))
    return cursor.lastrowid

def create_workflow_record(cursor, team_id: int, task_id: int, correlation_id: str) -> int:
    """Create workflow record and return workflow_id"""
    # Get the first agent from the team to use as initiator
    cursor.execute("""
        SELECT agent_id FROM team_agents 
        WHERE team_id = %s 
        ORDER BY priority DESC, accuracy DESC, success DESC 
        LIMIT 1
    """, (team_id,))
    result = cursor.fetchone()
    if not result:
        raise ValueError(f"No agents found for team {team_id}")
    
    initiator_id = result['agent_id']
    
    cursor.execute("""
        INSERT INTO workflows (
            initiator_id, 
            type, 
            status, 
            message,
            team_id, 
            correlation_id, 
            task_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        initiator_id,
        'sequential',  # Default type
        'pending',
        'Team task execution',
        team_id,
        correlation_id,
        json.dumps({'task_id': task_id})
    ))
    return cursor.lastrowid

def get_team_agents_ordered(cursor, team_id: int) -> List[Dict[str, Any]]:
    """Get team agents ordered by priority, accuracy, and success rate"""
    cursor.execute("""
        SELECT ta.agent_id, ta.priority, ta.accuracy, ta.success, a.name
        FROM team_agents ta
        JOIN agents a ON ta.agent_id = a.id
        WHERE ta.team_id = %s
        ORDER BY ta.priority DESC, ta.accuracy DESC, ta.success DESC
    """, (team_id,))
    return cursor.fetchall()

def group_agents_by_priority(agents: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """Group agents by priority level"""
    priority_groups = defaultdict(list)
    for agent in agents:
        priority_groups[agent['priority']].append(agent)
    return dict(sorted(priority_groups.items(), reverse=True))

def create_workflow_steps(cursor, workflow_id: int, agents: List[Dict[str, Any]]) -> List[int]:
    """Create workflow steps for a group of agents and return step_ids"""
    step_ids = []
    for idx, agent in enumerate(agents, 1):  # Start enumeration from 1
        cursor.execute("""
            INSERT INTO workflow_steps (
                workflow_id, 
                agent_id, 
                step_order,
                status
            ) VALUES (%s, %s, %s, %s)
        """, (
            workflow_id,
            agent['agent_id'],
            idx,  # Use enumeration index as step_order
            'pending'
        ))
        step_ids.append(cursor.lastrowid)
    return step_ids

def execute_agent_task(agent: Dict[str, Any], task: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """Execute task with a single agent"""
    try:
        # Initialize agent from database
        agent_instance = initialize_agent_from_db(agent['agent_id'])
        if not agent_instance:
            raise ValueError(f"Failed to initialize agent {agent['agent_id']}")
        
        # Set correlation ID for tracking
        agent_instance.set_correlation_id(correlation_id)
        
        # Prepare message with context
        message = {
            "task_description": task.get('description', ''),
            "requirements": task.get('requirements', {}),
            "agent_config": {
                "accuracy_threshold": agent.get('accuracy', 0.8),
                "success_rate": agent.get('success', 0.9),
                "priority": agent.get('priority', 3)
            }
        }
        
        # Execute with agent's tools
        result = agent_instance.execute_with_tools(json.dumps(message))
        
        # Format response
        return {
            'agent_id': agent['agent_id'],
            'agent_name': agent.get('name', f"Agent_{agent['agent_id']}"),
            'status': result.get('status', 'failed'),
            'response': {
                'message': result.get('message', ''),
                'data': result.get('data', {}),
                'tool_results': result.get('tool_results', []),
                'llm_response': result.get('llm_response', '')
            }
        }
    except Exception as e:
        logger.error(f"Error executing agent task: {str(e)}", exc_info=True)
        return {
            'agent_id': agent['agent_id'],
            'agent_name': agent.get('name', f"Agent_{agent['agent_id']}"),
            'status': 'failed',
            'error': str(e)
        }

def execute_priority_group(agents: List[Dict[str, Any]], step_ids: List[int], task: Dict[str, Any], correlation_id: str) -> List[Dict[str, Any]]:
    """Execute tasks in parallel for agents in the same priority group"""
    responses = []
    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        future_to_agent = {
            executor.submit(execute_agent_task, agent, task, correlation_id): agent
            for agent in agents
        }
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            try:
                response = future.result()
                responses.append(response)
            except Exception as e:
                logger.error(f"Error in agent execution: {str(e)}")
                responses.append({
                    'agent_id': agent['agent_id'],
                    'status': 'failed',
                    'error': str(e)
                })
    return responses

def update_workflow_steps_status(cursor, step_ids: List[int], status: str):
    """Update status of workflow steps"""
    if step_ids:
        placeholders = ', '.join(['%s'] * len(step_ids))
        cursor.execute(f"""
            UPDATE workflow_steps
            SET status = %s, updated_at = %s
            WHERE id IN ({placeholders})
        """, [status, datetime.now()] + step_ids)

def update_workflow_status(cursor, workflow_id: int, status: str):
    """Update workflow status"""
    cursor.execute("""
        UPDATE workflows
        SET status = %s, updated_at = %s
        WHERE id = %s
    """, (status, datetime.now(), workflow_id))

def aggregate_team_responses(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate responses from multiple agents"""
    # Consider both 'completed' and 'success' as successful statuses
    successful_responses = [r for r in responses if r['status'] in ['completed', 'success']]
    failed_responses = [r for r in responses if r['status'] not in ['completed', 'success']]
    
    if not successful_responses:
        error_messages = []
        for r in failed_responses:
            if 'error' in r:
                error_messages.append(r['error'])
            elif 'response' in r and 'message' in r['response']:
                error_messages.append(r['response']['message'])
        
        return {
            'status': 'failed',
            'message': 'All agents failed to process the task',
            'data': {'errors': error_messages},
            'tool_results': [],
            'results': [],
            'conversation_context': [],
            'final_status': 'failed',
            'execution_summary': {
                'total_agents': len(responses),
                'successful_executions': 0,
                'priority_groups': [],
                'execution_order': []
            }
        }
    
    # Combine responses from all successful agents
    combined_data = {}
    combined_tool_results = []
    messages = []
    results = []
    conversation_context = []
    priority_groups = set()
    execution_order = []
    
    for response in successful_responses:
        # Extract agent details
        agent_details = {
            'agent_id': response.get('agent_id'),
            'agent_name': response.get('agent_name'),
            'priority': response.get('priority', 0),
            'accuracy': response.get('accuracy', 0),
            'success_rate': response.get('success_rate', 0)
        }
        
        # Add to results
        result = {
            **agent_details,
            'result': {
                'status': 'success',
                'llm_response': response.get('response', {}).get('llm_response', ''),
                'tool_results': response.get('response', {}).get('tool_results', [])
            }
        }
        results.append(result)
        
        # Add to conversation context
        context = {
            **agent_details,
            'response': response.get('response', {}).get('llm_response', '')
        }
        conversation_context.append(context)
        
        # Track priority groups and execution order
        priority = agent_details['priority']
        priority_groups.add(priority)
        
        # Update execution order
        order_entry = next(
            (entry for entry in execution_order if entry['priority'] == priority),
            None
        )
        if order_entry:
            order_entry['agents'].append(f"{agent_details['agent_name']} (ID: {agent_details['agent_id']})")
        else:
            execution_order.append({
                'priority': priority,
                'agents': [f"{agent_details['agent_name']} (ID: {agent_details['agent_id']})"]
            })
        
        # Combine other data
        if 'response' in response:
            if 'message' in response['response']:
                messages.append(response['response']['message'])
            if 'data' in response['response']:
                combined_data.update(response['response']['data'])
            if 'tool_results' in response['response']:
                combined_tool_results.extend(response['response']['tool_results'])
            if 'llm_response' in response['response']:
                messages.append(response['response']['llm_response'])
    
    return {
        'status': 'success',
        'message': ' | '.join(messages) if messages else 'Task completed successfully',
        'data': combined_data,
        'tool_results': combined_tool_results,
        'results': results,
        'conversation_context': conversation_context,
        'final_status': 'completed',
        'execution_summary': {
            'total_agents': len(responses),
            'successful_executions': len(successful_responses),
            'priority_groups': sorted(list(priority_groups), reverse=True),
            'execution_order': sorted(execution_order, key=lambda x: x['priority'], reverse=True)
        }
    } 