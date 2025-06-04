from typing import Dict, Any, List
from app.models.team import Team, TeamTask
from app.services.agent_service import initialize_agent_from_db
from app.utils.logger import logger
from datetime import datetime
import json

def execute_task_with_team(team: Team, task: TeamTask) -> Dict[str, Any]:
    """
    Execute a task using a team of agents.
    Args:
        team: The team to execute the task
        task: The task to execute
    Returns:
        Dictionary containing execution results
    """
    start_time = datetime.utcnow()
    conversation_context: List[Dict[str, Any]] = []
    
    try:
        logger.info(f"Starting task execution with team {team.team_id}")
        
        # Initialize all team members
        active_agents = []
        for agent_id in team.members:
            try:
                agent = initialize_agent_from_db(agent_id)
                if agent:
                    active_agents.append(agent)
                    logger.info(f"Agent {agent_id} initialized for task {task.task_id}")
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent_id}: {str(e)}")
        
        if not active_agents:
            raise ValueError("No active agents available for task execution")
        
        # Process task requirements
        task_context = {
            'task_id': task.task_id,
            'description': task.description,
            'requirements': task.requirements,
            'team_size': len(active_agents),
            'start_time': start_time.isoformat()
        }
        
        # Execute task with each agent
        for agent in active_agents:
            try:
                # Prepare agent context
                agent_context = {
                    'agent_id': agent.agent_id,
                    'name': agent.name,
                    'tools': [t._asdict() for t in agent.tools],
                    'task': task_context
                }
                
                # Execute agent's part of the task
                agent_result = execute_agent_task(agent, task, agent_context)
                
                # Record interaction in conversation context
                conversation_context.append({
                    'agent_id': agent.agent_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'context': agent_context,
                    'result': agent_result
                })
                
                logger.info(f"Agent {agent.agent_id} completed their part of task {task.task_id}")
                
            except Exception as e:
                logger.error(f"Error during agent {agent.agent_id} execution: {str(e)}")
                conversation_context.append({
                    'agent_id': agent.agent_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': str(e)
                })
        
        # Calculate final status based on conversation context
        successful_agents = sum(1 for c in conversation_context if 'error' not in c)
        final_status = 'completed' if successful_agents == len(active_agents) else 'partial'
        
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # Update team metrics
        team.update_metrics(final_status == 'completed', execution_time)
        
        return {
            'final_status': final_status,
            'execution_time': execution_time,
            'successful_agents': successful_agents,
            'total_agents': len(active_agents),
            'conversation_context': conversation_context,
            'task_context': task_context,
            'completion_time': end_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Task execution failed: {str(e)}")
        return {
            'final_status': 'failed',
            'error': str(e),
            'conversation_context': conversation_context
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
        response = openai.ChatCompletion.create(
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