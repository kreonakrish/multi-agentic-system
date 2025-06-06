from typing import Dict, Any, List
from datetime import datetime
import json
from app.utils.logger import logger
from app.utils.db import get_db_connection, safe_close_connection
from app.models.team import Team, TeamTask
from app.services.agent_service import initialize_agent_from_db
from concurrent.futures import ThreadPoolExecutor, as_completed

class WorkflowManager:
    def __init__(self, team: Team, task: TeamTask):
        self.team = team
        self.task = task
        self.workflow_id = None
        self.correlation_id = task.task_id
        
    def initialize_workflow(self) -> Dict[str, Any]:
        """Initialize workflow record and return workflow ID"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Create workflow record
            cursor.execute("""
                INSERT INTO workflows (
                    initiator_id, type, status, message, created_at
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                self.team.team_id,
                'sequential',
                'pending',
                self.task.description,
                datetime.now()
            ))
            self.workflow_id = cursor.lastrowid
            
            # Get all agents for the team with their metrics
            cursor.execute("""
                SELECT ta.agent_id, ta.accuracy, ta.success, ta.priority,
                       a.name as agent_name
                FROM team_agents ta
                JOIN agents a ON ta.agent_id = a.id
                WHERE ta.team_id = %s
                ORDER BY ta.priority DESC, ta.accuracy DESC, ta.success DESC
            """, (self.team.team_id,))
            
            agents = cursor.fetchall()
            
            # Create workflow steps for each agent
            for idx, agent in enumerate(agents, 1):
                cursor.execute("""
                    INSERT INTO workflow_steps (
                        workflow_id, agent_id, step_order, status
                    ) VALUES (%s, %s, %s, %s)
                """, (
                    self.workflow_id,
                    agent['agent_id'],
                    idx,
                    'pending'
                ))
            
            conn.commit()
            logger.info(f"Initialized workflow {self.workflow_id} with {len(agents)} steps")
            
            return {
                "status": "success",
                "workflow_id": self.workflow_id,
                "agents": agents
            }
            
        except Exception as e:
            logger.error(f"Error initializing workflow: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
            raise
        finally:
            safe_close_connection(conn, cursor)
    
    def execute_workflow(self) -> Dict[str, Any]:
        """Execute the workflow with proper agent ordering and response aggregation"""
        try:
            # Initialize workflow
            workflow_init = self.initialize_workflow()
            if workflow_init["status"] != "success":
                return workflow_init
            
            agents = workflow_init["agents"]
            final_results = []
            conversation_context = []
            
            # Update workflow status to in_progress
            self._update_workflow_status("in_progress")
            
            # Execute agents in priority order
            for agent_data in agents:
                try:
                    # Update workflow step status
                    self._update_step_status(agent_data['agent_id'], "in_progress")
                    
                    # Initialize agent
                    agent = initialize_agent_from_db(agent_data['agent_id'])
                    if not agent:
                        logger.error(f"Could not initialize agent {agent_data['agent_id']}")
                        self._update_step_status(agent_data['agent_id'], "failed")
                        continue
                    
                    # Set correlation ID
                    agent.set_correlation_id(self.correlation_id)
                    
                    # Prepare message with context
                    message = {
                        "task_description": self.task.description,
                        "requirements": self.task.requirements,
                        "conversation_context": conversation_context,
                        "accuracy_threshold": agent_data['accuracy'],
                        "success_rate": agent_data['success'],
                        "priority": agent_data['priority']
                    }
                    
                    # Execute agent's tools
                    result = agent.execute_with_tools(json.dumps(message))
                    
                    if result.get("status") == "success":
                        # Store tool responses
                        self._store_tool_responses(agent_data['agent_id'], result)
                        
                        # Update workflow step status
                        self._update_step_status(agent_data['agent_id'], "completed")
                        
                        # Add to conversation context
                        context_entry = {
                            "agent_id": agent_data['agent_id'],
                            "agent_name": agent_data['agent_name'],
                            "priority": agent_data['priority'],
                            "accuracy": agent_data['accuracy'],
                            "success_rate": agent_data['success'],
                            "response": result.get("llm_response", "")
                        }
                        conversation_context.append(context_entry)
                        
                        # Add to final results
                        result_entry = {
                            "agent_id": agent_data['agent_id'],
                            "agent_name": agent_data['agent_name'],
                            "priority": agent_data['priority'],
                            "accuracy": agent_data['accuracy'],
                            "success_rate": agent_data['success'],
                            "result": result
                        }
                        final_results.append(result_entry)
                        
                    else:
                        logger.warning(f"Agent {agent_data['agent_id']} execution failed")
                        self._update_step_status(agent_data['agent_id'], "failed")
                        
                except Exception as e:
                    logger.error(f"Error executing agent {agent_data['agent_id']}: {str(e)}", exc_info=True)
                    self._update_step_status(agent_data['agent_id'], "failed")
            
            # Update workflow status
            final_status = "completed" if any(r["result"].get("status") == "success" for r in final_results) else "failed"
            self._update_workflow_status(final_status)
            
            return {
                "status": "success",
                "workflow_id": self.workflow_id,
                "final_status": final_status,
                "results": final_results,
                "conversation_context": conversation_context
            }
            
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}", exc_info=True)
            if self.workflow_id:
                self._update_workflow_status("failed")
            return {
                "status": "error",
                "message": str(e)
            }
    
    def _update_workflow_status(self, status: str):
        """Update workflow status"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE workflows
                SET status = %s, updated_at = %s
                WHERE id = %s
            """, (status, datetime.now(), self.workflow_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating workflow status: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
        finally:
            safe_close_connection(conn, cursor)
    
    def _update_step_status(self, agent_id: int, status: str):
        """Update workflow step status"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE workflow_steps
                SET status = %s, updated_at = %s
                WHERE workflow_id = %s AND agent_id = %s
            """, (status, datetime.now(), self.workflow_id, agent_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating step status: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
        finally:
            safe_close_connection(conn, cursor)
    
    def _store_tool_responses(self, agent_id: int, result: Dict[str, Any]):
        """Store tool responses in workflow_steps"""
        conn = None
        cursor = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE workflow_steps
                SET tool_responses = %s, updated_at = %s
                WHERE workflow_id = %s AND agent_id = %s
            """, (json.dumps(result), datetime.now(), self.workflow_id, agent_id))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing tool responses: {str(e)}", exc_info=True)
            if conn:
                conn.rollback()
        finally:
            safe_close_connection(conn, cursor)

def store_team_task(cursor, team_id: int, task: Dict[str, Any], correlation_id: str) -> int:
    """Store team task record and return task_id"""
    cursor.execute("""
        INSERT INTO team_tasks (team_id, task_description, correlation_id, created_at)
        VALUES (%s, %s, %s, NOW())
    """, (team_id, json.dumps(task), correlation_id))
    return cursor.lastrowid

def create_workflow_record(cursor, team_id: int, task_id: int, correlation_id: str) -> int:
    """Create workflow record and return workflow_id"""
    cursor.execute("""
        INSERT INTO workflows (team_id, task_id, correlation_id, status, created_at)
        VALUES (%s, %s, %s, 'pending', NOW())
    """, (team_id, task_id, correlation_id))
    return cursor.lastrowid

def get_team_agents_ordered(cursor, team_id: int) -> List[Dict[str, Any]]:
    """Get team agents ordered by priority, accuracy, and success rate"""
    cursor.execute("""
        SELECT a.*, ta.priority, ta.accuracy_rate, ta.success_rate
        FROM agents a
        JOIN team_agents ta ON a.id = ta.agent_id
        WHERE ta.team_id = %s
        ORDER BY ta.priority DESC, ta.accuracy_rate DESC, ta.success_rate DESC
    """, (team_id,))
    return cursor.fetchall()

def group_agents_by_priority(agents: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
    """Group agents by priority level"""
    priority_groups = {}
    for agent in agents:
        if agent['priority'] not in priority_groups:
            priority_groups[agent['priority']] = []
        priority_groups[agent['priority']].append(agent)
    return dict(sorted(priority_groups.items(), reverse=True))

def create_workflow_steps(cursor, workflow_id: int, agents: List[Dict[str, Any]]) -> List[int]:
    """Create workflow steps for agents and return step IDs"""
    step_ids = []
    for agent in agents:
        cursor.execute("""
            INSERT INTO workflow_steps 
            (workflow_id, agent_id, status, created_at)
            VALUES (%s, %s, 'pending', NOW())
        """, (workflow_id, agent['id']))
        step_ids.append(cursor.lastrowid)
    return step_ids

def execute_priority_group(
    agents: List[Dict[str, Any]], 
    step_ids: List[int],
    task: Dict[str, Any],
    correlation_id: str
) -> List[Dict[str, Any]]:
    """Execute agents in a priority group in parallel"""
    responses = []
    with ThreadPoolExecutor(max_workers=len(agents)) as executor:
        future_to_agent = {
            executor.submit(
                execute_agent_task, 
                agent, 
                step_id,
                task,
                correlation_id
            ): agent for agent, step_id in zip(agents, step_ids)
        }
        for future in as_completed(future_to_agent):
            agent = future_to_agent[future]
            try:
                response = future.result()
                responses.append({
                    'agent_id': agent['id'],
                    'agent_priority': agent['priority'],
                    'agent_accuracy': agent['accuracy_rate'],
                    'agent_success': agent['success_rate'],
                    'response': response
                })
            except Exception as e:
                logger.error(f"Error executing agent {agent['id']}: {str(e)}",
                           extra={"correlation_id": correlation_id})
    return responses

def execute_agent_task(
    agent: Dict[str, Any], 
    step_id: int,
    task: Dict[str, Any],
    correlation_id: str
) -> Dict[str, Any]:
    """Execute a single agent's task"""
    try:
        # Initialize agent with tools
        agent_instance = initialize_agent_from_db(agent)
        agent_instance.correlation_id = correlation_id
        
        # Execute agent's task
        response = agent_instance.execute_with_tools(task)
        
        # Store tool responses
        store_tool_responses(step_id, response.get('tool_results', []))
        
        return response
        
    except Exception as e:
        logger.error(f"Error in execute_agent_task: {str(e)}",
                    extra={"correlation_id": correlation_id})
        raise

def store_tool_responses(step_id: int, tool_results: List[Dict[str, Any]]) -> None:
    """Store tool responses in workflow_steps"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE workflow_steps 
            SET tool_responses = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (json.dumps(tool_results), step_id))
        
        conn.commit()
        
    finally:
        safe_close_connection(conn, cursor)

def update_workflow_steps_status(cursor, step_ids: List[int], status: str) -> None:
    """Update status of workflow steps"""
    placeholders = ','.join(['%s'] * len(step_ids))
    cursor.execute(f"""
        UPDATE workflow_steps 
        SET status = %s,
            updated_at = NOW()
        WHERE id IN ({placeholders})
    """, [status] + step_ids)

def update_workflow_status(cursor, workflow_id: int, status: str) -> None:
    """Update workflow status"""
    cursor.execute("""
        UPDATE workflows 
        SET status = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (status, workflow_id))

def aggregate_team_responses(responses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate responses from all agents into final team response"""
    # Sort responses by agent priority/accuracy/success
    sorted_responses = sorted(
        responses,
        key=lambda x: (
            x.get('agent_priority', 0),
            x.get('agent_accuracy', 0),
            x.get('agent_success', 0)
        ),
        reverse=True
    )
    
    # Combine responses
    combined_response = {
        'message': '',
        'data': {},
        'tool_results': []
    }
    
    for response in sorted_responses:
        agent_response = response.get('response', {})
        
        # Append message
        if agent_response.get('message'):
            combined_response['message'] += f"\n{agent_response['message']}"
            
        # Merge data
        if agent_response.get('data'):
            combined_response['data'].update(agent_response['data'])
            
        # Collect tool results
        if agent_response.get('tool_results'):
            combined_response['tool_results'].extend(agent_response['tool_results'])
    
    return combined_response 