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
        logger.info(f"[execute_task_with_team] Starting task execution")
        logger.info(f"[execute_task_with_team] Team ID: {team.team_id}")
        logger.info(f"[execute_task_with_team] Task ID: {task.task_id}")
        logger.info(f"[execute_task_with_team] Task Description: {task.description}")
        logger.debug(f"[execute_task_with_team] Task Requirements: {json.dumps(task.requirements, indent=2)}")
        
        # Initialize all team members and sort them by priority, accuracy, and success rate
        active_agents = []
        logger.info("[execute_task_with_team] Initializing team members...")
        
        for member in team.members:
            try:
                logger.info(f"[execute_task_with_team] Initializing member - Agent ID: {member.agent_id}, "
                          f"Priority: {member.priority.value}, Accuracy: {member.accuracy_threshold}, "
                          f"Success Rate: {member.success_rate}")
                
                agent = initialize_agent_from_db(member.agent_id)
                if agent:
                    # Store member properties with the agent for sorting
                    agent.priority = member.priority.value
                    agent.accuracy_threshold = member.accuracy_threshold
                    agent.success_rate = member.success_rate
                    active_agents.append(agent)
                    logger.info(f"[execute_task_with_team] Successfully initialized agent {member.agent_id}")
                else:
                    logger.warning(f"[execute_task_with_team] Agent {member.agent_id} initialization returned None")
            except Exception as e:
                logger.error(f"[execute_task_with_team] Failed to initialize agent {member.agent_id}: {str(e)}", 
                           exc_info=True)
        
        if not active_agents:
            logger.error("[execute_task_with_team] No active agents available for task execution")
            raise ValueError("No active agents available for task execution")
            
        # Sort agents by priority (highest first), accuracy (highest first), and success rate (highest first)
        active_agents.sort(key=lambda x: (-x.priority, -x.accuracy_threshold, -x.success_rate))
        logger.info("[execute_task_with_team] Agents sorted by priority, accuracy, and success rate")
        logger.info("Execution order:")
        for idx, agent in enumerate(active_agents, 1):
            logger.info(f"  {idx}. Agent {agent.agent_id} - Priority: {agent.priority}, "
                       f"Accuracy: {agent.accuracy_threshold}, Success Rate: {agent.success_rate}")
        
        # Execute task with sorted agents
        successful_agents = 0
        final_results = []
        
        for idx, agent in enumerate(active_agents, 1):
            try:
                logger.info(f"\n[execute_task_with_team] Executing agent {idx}/{len(active_agents)}")
                logger.info(f"[execute_task_with_team] Agent details - ID: {agent.agent_id}, "
                          f"Priority: {agent.priority}, Accuracy: {agent.accuracy_threshold}, "
                          f"Success Rate: {agent.success_rate}")
                
                # Prepare message with context
                message = {
                    "task_description": task.description,
                    "requirements": task.requirements,
                    "conversation_context": conversation_context
                }
                
                logger.debug(f"[execute_task_with_team] Sending message to agent: {json.dumps(message, indent=2)}")
                
                # Execute with agent
                result = agent.execute_with_tools(json.dumps(message))
                logger.info(f"[execute_task_with_team] Received result from agent {agent.agent_id}")
                logger.debug(f"[execute_task_with_team] Agent result: {json.dumps(result, indent=2)}")
                
                if result.get("status") == "success":
                    successful_agents += 1
                    logger.info(f"[execute_task_with_team] Agent {agent.agent_id} execution successful")
                    
                    # Extract response text for context
                    response_text = result.get("llm_response", "")
                    if isinstance(response_text, dict):
                        response_text = json.dumps(response_text)
                    
                    # Add to conversation context
                    context_entry = {
                        "agent_id": agent.agent_id,
                        "priority": agent.priority,
                        "accuracy": agent.accuracy_threshold,
                        "success_rate": agent.success_rate,
                        "response": response_text
                    }
                    conversation_context.append(context_entry)
                    logger.debug(f"[execute_task_with_team] Added to conversation context: {json.dumps(context_entry, indent=2)}")
                    
                    # Add to final results
                    result_entry = {
                        "agent_id": agent.agent_id,
                        "priority": agent.priority,
                        "accuracy": agent.accuracy_threshold,
                        "success_rate": agent.success_rate,
                        "result": result
                    }
                    final_results.append(result_entry)
                    logger.debug(f"[execute_task_with_team] Added to final results: {json.dumps(result_entry, indent=2)}")
                else:
                    logger.warning(f"[execute_task_with_team] Agent {agent.agent_id} execution failed")
                    logger.warning(f"[execute_task_with_team] Failure details: {json.dumps(result, indent=2)}")
                    
            except Exception as e:
                logger.error(f"[execute_task_with_team] Error with agent {agent.agent_id}: {str(e)}", exc_info=True)
                continue
        
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # Determine final status
        final_status = "completed" if successful_agents > 0 else "failed"
        logger.info(f"[execute_task_with_team] Task execution completed")
        logger.info(f"[execute_task_with_team] Final status: {final_status}")
        logger.info(f"[execute_task_with_team] Execution time: {execution_time:.2f} seconds")
        logger.info(f"[execute_task_with_team] Successful agents: {successful_agents}/{len(active_agents)}")
        
        result = {
            'final_status': final_status,
            'execution_time': execution_time,
            'successful_agents': successful_agents,
            'total_agents': len(active_agents),
            'conversation_context': conversation_context,
            'results': final_results,
            'completion_time': end_time.isoformat()
        }
        
        logger.debug(f"[execute_task_with_team] Final result: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"[execute_task_with_team] Task execution failed with error: {str(e)}", exc_info=True)
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