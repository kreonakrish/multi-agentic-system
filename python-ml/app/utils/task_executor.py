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
    priority_groups = {}
    execution_order = []
    workflow_id = None
    final_results = []
    
    try:
        logger.info("="*80)
        logger.info(f"[TEAM EXECUTION START] Task ID: {task.task_id} | Team ID: {team.team_id}")
        logger.info("="*80)
        logger.info(f"[TASK DETAILS] Description: {task.description}")
        logger.debug(f"[TASK REQUIREMENTS] {json.dumps(task.requirements, indent=2)}")
        
        # Create workflow record
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                INSERT INTO workflows (
                    correlation_id,
                    team_id,
                    status,
                    task_data,
                    created_at
                ) VALUES (%s, %s, %s, %s, NOW())
            """, (
                task.task_id,
                team.team_id,
                'pending',
                json.dumps({
                    'description': task.description,
                    'requirements': task.requirements
                })
            ))
            
            workflow_id = cursor.lastrowid
            logger.info(f"[WORKFLOW] Created workflow record with ID: {workflow_id}")
            
            conn.commit()
        except Exception as e:
            logger.error(f"[WORKFLOW] Error creating workflow record: {str(e)}", exc_info=True)
            raise
        finally:
            safe_close_connection(conn, cursor)
        
        # Get conversation settings
        logger.info("[FETCHING CONVERSATION SETTINGS]")
        conversation_settings = task.requirements.get('conversation_settings_id')
        end_prompt = None
        if conversation_settings:
            try:
                logger.debug(f"[CONVERSATION SETTINGS] Fetching settings for ID: {conversation_settings}")
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT end_prompt FROM conversation_settings 
                    WHERE id = %s
                """, (conversation_settings,))
                result = cursor.fetchone()
                if result:
                    end_prompt = result['end_prompt']
                    logger.info("[CONVERSATION SETTINGS] Successfully retrieved end_prompt")
                    logger.debug(f"[CONVERSATION SETTINGS] End Prompt: {end_prompt}")
                else:
                    logger.warning(f"[CONVERSATION SETTINGS] No settings found for ID: {conversation_settings}")
                safe_close_connection(conn, cursor)
            except Exception as e:
                logger.error(f"[CONVERSATION SETTINGS] Error fetching settings: {str(e)}", exc_info=True)
        else:
            logger.info("[CONVERSATION SETTINGS] No conversation_settings_id provided in requirements")
        
        # Initialize team members
        logger.info("\n[TEAM INITIALIZATION] Starting team member initialization")
        active_agents = []
        
        # Get all agents for the team with their metrics
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ta.agent_id, ta.accuracy, ta.success, ta.priority,
                   a.name as agent_name
            FROM team_agents ta
            JOIN agents a ON ta.agent_id = a.id
            WHERE ta.team_id = %s
            ORDER BY ta.priority DESC, ta.accuracy DESC, ta.success DESC
        """, (team.team_id,))
        
        agents = cursor.fetchall()
        safe_close_connection(conn, cursor)
        
        # Group agents by priority
        current_priority = None
        current_group = []
        
        for agent in agents:
            if current_priority is None:
                current_priority = agent['priority']
            
            if agent['priority'] != current_priority:
                priority_groups[current_priority] = current_group
                execution_order.append({
                    "priority": current_priority,
                    "agents": [f"{a['agent_name']} (ID: {a['agent_id']})" for a in current_group]
                })
                current_group = []
                current_priority = agent['priority']
            
            current_group.append(agent)
            active_agents.append(agent)
        
        if current_group:
            priority_groups[current_priority] = current_group
            execution_order.append({
                "priority": current_priority,
                "agents": [f"{a['agent_name']} (ID: {a['agent_id']})" for a in current_group]
            })
        
        logger.info(f"[TEAM INITIALIZATION] Successfully initialized {len(active_agents)} agents")
        
        # Execute task with sorted agents
        successful_agents = 0
        
        logger.info("\n[AGENT EXECUTION] Starting individual agent executions")
        for idx, agent in enumerate(active_agents, 1):
            try:
                logger.info("-"*60)
                logger.info(f"[AGENT {idx}/{len(active_agents)}] Starting execution for Agent: {agent['agent_id']}")
                logger.info(f"[AGENT {idx}/{len(active_agents)}] Details:")
                logger.info(f"  - Name: {agent['agent_name']}")
                logger.info(f"  - Priority: {agent['priority']}")
                logger.info(f"  - Accuracy: {agent['accuracy']}")
                logger.info(f"  - Success Rate: {agent['success']}")
                
                # Create workflow step
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO workflow_steps (
                            workflow_id,
                            agent_id,
                            status,
                            created_at
                        ) VALUES (%s, %s, %s, NOW())
                    """, (workflow_id, agent['agent_id'], 'in_progress'))
                    step_id = cursor.lastrowid
                    conn.commit()
                    logger.info(f"[WORKFLOW] Created step {step_id} for agent {agent['agent_id']}")
                except Exception as e:
                    logger.error(f"[WORKFLOW] Error creating workflow step: {str(e)}", exc_info=True)
                finally:
                    safe_close_connection(conn, cursor)
                
                # Prepare message with context
                message = {
                    "task_description": task.description,
                    "requirements": task.requirements,
                    "conversation_context": conversation_context,
                    "agent_config": {
                        "accuracy_threshold": agent['accuracy'],
                        "success_rate": agent['success'],
                        "priority": agent['priority']
                    }
                }
                logger.debug(f"[AGENT {idx}/{len(active_agents)}] Prepared message: {json.dumps(message, indent=2)}")
                
                # Execute with agent
                logger.info(f"[AGENT {idx}/{len(active_agents)}] Executing with tools...")
                agent_instance = initialize_agent_from_db(agent['agent_id'])
                if not agent_instance:
                    raise ValueError(f"Could not initialize agent {agent['agent_id']}")
                
                result = agent_instance.execute_with_tools(json.dumps(message))
                logger.info(f"[AGENT {idx}/{len(active_agents)}] Execution completed")
                logger.debug(f"[AGENT {idx}/{len(active_agents)}] Raw result: {json.dumps(result, indent=2)}")
                
                # Update workflow step
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE workflow_steps 
                        SET status = %s,
                            tool_responses = %s,
                            updated_at = NOW()
                        WHERE workflow_id = %s AND agent_id = %s
                    """, (
                        'completed' if result.get("status") == "success" else 'failed',
                        json.dumps(result.get('tool_results', [])),
                        workflow_id,
                        agent['agent_id']
                    ))
                    conn.commit()
                except Exception as e:
                    logger.error(f"[WORKFLOW] Error updating workflow step: {str(e)}", exc_info=True)
                finally:
                    safe_close_connection(conn, cursor)
                
                if result.get("status") == "success":
                    successful_agents += 1
                    logger.info(f"[AGENT {idx}/{len(active_agents)}] Execution successful")
                else:
                    logger.warning(f"[AGENT {idx}/{len(active_agents)}] Execution failed")
                    logger.warning(f"[AGENT {idx}/{len(active_agents)}] Failure reason: {result.get('error', 'Unknown')}")
                
                # Add to conversation context
                context_entry = {
                    "agent_id": agent['agent_id'],
                    "agent_name": agent['agent_name'],
                    "priority": agent['priority'],
                    "accuracy": agent['accuracy'],
                    "success_rate": agent['success'],
                    "response": result.get('llm_response', '')
                }
                conversation_context.append(context_entry)
                logger.debug(f"[AGENT {idx}/{len(active_agents)}] Added to conversation context: {json.dumps(context_entry, indent=2)}")
                
                # Add to final results
                result_entry = {
                    "agent_id": agent['agent_id'],
                    "agent_name": agent['agent_name'],
                    "priority": agent['priority'],
                    "accuracy": agent['accuracy'],
                    "success_rate": agent['success'],
                    "result": {
                        "status": result.get("status", "failed"),
                        "llm_response": result.get("llm_response", ""),
                        "tool_results": result.get("tool_results", [])
                    }
                }
                final_results.append(result_entry)
                logger.debug(f"[AGENT {idx}/{len(active_agents)}] Added to final results: {json.dumps(result_entry, indent=2)}")
                
            except Exception as e:
                logger.error(f"[AGENT {idx}/{len(active_agents)}] Execution error: {str(e)}", exc_info=True)
                continue
        
        # Determine final status
        logger.info("[TEAM VALIDATION] Determining final status")
        final_status = "completed" if successful_agents > 0 else "failed"
        logger.info(f"[TEAM VALIDATION] Final status determined: {final_status}")
        
        # Update workflow status
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflows 
                SET status = %s,
                    response_data = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                final_status,
                json.dumps({
                    'results': final_results,
                    'conversation_context': conversation_context
                }),
                workflow_id
            ))
            conn.commit()
            logger.info(f"[WORKFLOW] Updated workflow {workflow_id} status to {final_status}")
        except Exception as e:
            logger.error(f"[WORKFLOW] Error updating workflow status: {str(e)}", exc_info=True)
        finally:
            safe_close_connection(conn, cursor)
        
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        logger.info(f"[EXECUTION TIME] Total execution time: {execution_time:.2f} seconds")
        
        result = {
            'workflow_id': workflow_id,
            'final_status': final_status,
            'execution_time': execution_time,
            'successful_agents': successful_agents,
            'total_agents': len(active_agents),
            'conversation_context': conversation_context,
            'results': final_results,
            'priority_groups': sorted(priority_groups.keys(), reverse=True),
            'execution_order': execution_order
        }
        
        logger.info("\n[EXECUTION COMPLETE] Task execution completed successfully")
        logger.info(f"[EXECUTION SUMMARY]")
        logger.info(f"  - Final Status: {final_status}")
        logger.info(f"  - Execution Time: {execution_time:.2f} seconds")
        logger.info(f"  - Successful Agents: {successful_agents}/{len(active_agents)}")
        logger.info("="*80)
        
        logger.debug(f"[FINAL RESULT] {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error("[EXECUTION FAILED] Task execution failed with error", exc_info=True)
        logger.error(f"[ERROR DETAILS] {str(e)}")
        return {
            'workflow_id': workflow_id,
            'final_status': 'failed',
            'error': str(e),
            'conversation_context': conversation_context if 'conversation_context' in locals() else [],
            'results': final_results if 'final_results' in locals() else [],
            'total_agents': len(active_agents) if 'active_agents' in locals() else 0,
            'successful_agents': successful_agents if 'successful_agents' in locals() else 0,
            'priority_groups': sorted(priority_groups.keys(), reverse=True) if priority_groups else [],
            'execution_order': execution_order if 'execution_order' in locals() else []
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