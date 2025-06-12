"""Utility functions for team task execution"""
from typing import Dict, List, Any, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import json
import uuid
import logging
from app.utils.logger import logger
from app.services.agent_service import initialize_agent_from_db
from app.utils.db import get_db_connection, safe_close_connection
from app.utils.openai_utils import get_openai_client
from app.models.team import Team
from app.models.task import TeamTask

# Get workflow-specific loggers
workflow_logger = logging.getLogger('multi_agent_system.workflow')
workflow_steps_logger = logging.getLogger('multi_agent_system.workflow.steps')
workflow_execution_logger = logging.getLogger('multi_agent_system.workflow.execution')

# Get module-specific logger
logger = logging.getLogger(__name__)

def aggregate_team_responses(results: List[Dict[str, Any]], task_description: str) -> Dict[str, Any]:
    """Aggregate responses from all team members."""
    try:
        # Initialize aggregated data structure
        aggregated_data = {
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
        }
        
        # Process each agent's results
        for result in results:
            if result.get('status') == 'success':
                response = result.get('response', {})
                
                # Handle GitHub data specifically
                if 'github_data' in response:
                    github_data = response['github_data']
                    aggregated_data['raw_data']['samples'].append({
                        'tool': 'github',
                        'dataset': github_data.get('dataset_name', ''),
                        'data': github_data.get('data', [])[:3],  # First 3 rows as sample
                        'total_records': len(github_data.get('data', [])),
                        'schema': list(github_data.get('data', [{}])[0].keys()) if github_data.get('data') else []
                    })
                    aggregated_data['raw_data']['total_records'] += len(github_data.get('data', []))
                    
                    # Add dataset info to vector store results
                    aggregated_data['vector_store']['datasets'].append({
                        'name': github_data.get('dataset_name', ''),
                        'url': github_data.get('url', ''),
                        'info': github_data.get('dataset_info', {})
                    })
                
                # Add tool results
                if 'tool_results' in response:
                    aggregated_data['tool_results'].extend(response['tool_results'])
                
                # Add vector store results
                if 'vector_store_results' in response:
                    aggregated_data['vector_store']['results'].extend(response['vector_store_results'])
                
                # Add LLM response
                if 'llm_response' in response:
                    aggregated_data['llm_responses'].append({
                        'agent_id': result.get('agent_id'),
                        'response': response['llm_response']
                    })
        
        # Get validation from LLM
        validation_prompt = f"""
        Task Description: {task_description}
        
        Aggregated Results:
        {json.dumps(aggregated_data, indent=2)}
        
        Please analyze these results and provide:
        1. Response Quality and Consistency
        2. Data Completeness and Relevance
        3. Conflicts or Inconsistencies
        4. Vector Store Result Quality
        5. Raw Data Samples Quality
        
        Provide a detailed validation summary.
        """
        
        openai = get_openai_client()
        validation_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data validation expert."},
                {"role": "user", "content": validation_prompt}
            ],
            temperature=0.3
        )
        
        validation_text = validation_response.choices[0].message.content
        logger.info("Received validation response from LLM")
        logger.debug(f"Validation text: {validation_text}")
        
        # Check if validation passed
        validation_passed = True
        if "not complete" in validation_text.lower() or "missing" in validation_text.lower():
            validation_passed = False
        
        logger.info("Validation passed successfully" if validation_passed else "Validation failed")
        
        return {
            'aggregated_data': aggregated_data,
            'validation_result': validation_text,
            'validation_passed': validation_passed
        }
        
    except Exception as e:
        logger.error(f"Error in aggregate_team_responses: {str(e)}")
        return {
            'aggregated_data': {
                'vector_store': {'results': [], 'queries': [], 'datasets': []},
                'raw_data': {'samples': [], 'total_records': 0, 'schemas': []},
                'tool_results': [],
                'llm_responses': []
            },
            'validation_result': f"Error aggregating responses: {str(e)}",
            'validation_passed': False
        }

def store_team_task(cursor, team_id: int, task_data: Dict[str, Any], correlation_id: str) -> int:
    """Store team task in database and return task_id"""
    task_id = str(uuid.uuid4())  # Generate a unique task ID
    cursor.execute("""
        INSERT INTO team_tasks (
            task_id,
            team_id,
            task_type,
            complexity,
            description,
            requirements,
            priority,
            status,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        task_id,
        team_id,
        task_data.get('task_type', None),
        task_data.get('complexity', None),
        task_data.get('description', ''),
        json.dumps(task_data.get('requirements', {})),
        task_data.get('priority', 1),
        'pending',
        datetime.now(),
        datetime.now()
    ))
    workflow_logger.info(f"[WORKFLOW] Stored team task with ID: {task_id}")
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
        workflow_logger.error(f"[WORKFLOW] No agents found for team {team_id}")
        raise ValueError(f"No agents found for team {team_id}")
    
    initiator_id = result[0]  # Access first element of tuple
    start_time = datetime.now()
    
    cursor.execute("""
        INSERT INTO workflows (
            initiator_id, 
            type, 
            status, 
            message,
            team_id, 
            correlation_id, 
            task_data,
            start_time,
            end_time,
            execution_time,
            successful_agents,
            total_agents,
            error_message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, NULL, 0, 0, NULL)
    """, (
        initiator_id,
        'sequential',  # Default type
        'pending',
        'Team task execution',
        team_id,
        correlation_id,
        json.dumps({'task_id': task_id}),
        start_time
    ))
    workflow_id = cursor.lastrowid
    workflow_logger.info(f"[WORKFLOW] Created workflow record with ID: {workflow_id}")
    workflow_logger.info(f"[WORKFLOW] Status: INITIALIZED")
    workflow_logger.info(f"[WORKFLOW] Start Time: {start_time.isoformat()}")
    return workflow_id

def get_team_agents_ordered(cursor, team_id: int) -> List[Dict[str, Any]]:
    """Get ordered list of team agents"""
    cursor.execute("""
        SELECT ta.agent_id, ta.team_id, ta.priority, ta.accuracy, ta.success, a.name
        FROM team_agents ta 
        JOIN agents a ON ta.agent_id = a.id 
        WHERE ta.team_id = %s 
        ORDER BY ta.priority DESC, ta.accuracy DESC, ta.success DESC
    """, (team_id,))
    
    # Get column names from cursor description
    columns = [desc[0] for desc in cursor.description]
    results = cursor.fetchall()
    
    # Convert tuples to dictionaries with proper column names
    return [{
        columns[i]: value for i, value in enumerate(row)
    } for row in results]

def group_agents_by_priority(agents: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """Group agents by priority level"""
    priority_groups = defaultdict(list)
    for agent in agents:
        priority = agent['priority'] or 1  # Default to priority 1 if None
        priority_groups[priority].append(agent)
    return dict(priority_groups)

def create_workflow_steps(cursor, workflow_id: int, agents: List[Dict[str, Any]]) -> List[int]:
    """Create workflow steps for each agent"""
    step_ids = []
    for idx, agent in enumerate(agents, 1):
        cursor.execute("""
            INSERT INTO workflow_steps (
                workflow_id,
                agent_id,
                step_order,
                status,
                created_at,
                updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            workflow_id,
            agent['agent_id'],
            idx,
            'pending',
            datetime.now(),
            datetime.now()
        ))
        step_ids.append(cursor.lastrowid)
        workflow_steps_logger.info(f"[WORKFLOW_STEPS] Created step {idx} for agent {agent['agent_id']}")
    return step_ids

def update_workflow_steps_status(
    cursor,
    step_ids: List[int],
    status: str,
    error: Optional[str] = None,
    result: Optional[Dict[str, Any]] = None
) -> None:
    """Update status of workflow steps"""
    for step_id in step_ids:
        cursor.execute("""
            UPDATE workflow_steps 
            SET status = %s,
                error_message = %s,
                result = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            status,
            error,
            json.dumps(result) if result else None,
            datetime.now(),
            step_id
        ))
    workflow_steps_logger.info(f"[WORKFLOW_STEPS] Updated {len(step_ids)} steps to status: {status}")

def update_workflow_status(cursor, workflow_id: int, status: str) -> None:
    """Update workflow status"""
    cursor.execute("""
        UPDATE workflows 
        SET status = %s,
            end_time = %s,
            execution_time = TIMESTAMPDIFF(SECOND, start_time, %s)
        WHERE id = %s
    """, (
        status,
        datetime.now(),
        datetime.now(),
        workflow_id
    ))
    workflow_logger.info(f"[WORKFLOW] Updated workflow {workflow_id} status to: {status}")

def execute_priority_group(agents: List[Dict[str, Any]], step_ids: List[int], task: Dict[str, Any], correlation_id: str) -> List[Dict[str, Any]]:
    """Execute tasks in parallel for agents in the same priority group"""
    responses = []
    workflow_execution_logger.info(f"[WORKFLOW_EXECUTION] Starting execution of priority group with {len(agents)} agents")
    
    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        future_to_agent = {
            executor.submit(
                execute_agent_task, 
                agent, 
                task,
                correlation_id
            ): agent for agent in agents
        }
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            try:
                response = future.result()
                workflow_execution_logger.info(f"[WORKFLOW_EXECUTION] Agent {agent['agent_id']} completed execution")
                workflow_execution_logger.debug(f"[WORKFLOW_EXECUTION] Agent {agent['agent_id']} response: {json.dumps(response, indent=2)}")
                
                # Extract all data from the response
                agent_response = response.get('response', {})
                responses.append({
                    'agent_id': agent['agent_id'],
                    'agent_name': agent.get('name', f"Agent_{agent['agent_id']}"),
                    'status': response.get('status', 'failed'),
                    'response': {
                        'message': agent_response.get('message', ''),
                        'data': agent_response.get('data', {}),
                        'tool_results': agent_response.get('tool_results', []),
                        'llm_response': agent_response.get('llm_response', ''),
                        'vector_store_results': agent_response.get('vector_store_results', []),
                        'raw_data': agent_response.get('raw_data', {})
                    }
                })
                
            except Exception as e:
                workflow_execution_logger.error(f"[WORKFLOW_EXECUTION] Error executing agent {agent['agent_id']}: {str(e)}")
                responses.append({
                    'agent_id': agent['agent_id'],
                    'agent_name': agent.get('name', f"Agent_{agent['agent_id']}"),
                    'status': 'failed',
                    'error': str(e)
                })
    
    return responses

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