"""Agent coordinator for managing agent collaboration and task assignment."""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from app.models.team import Team, TeamTask
from app.utils.db import get_db_connection
from app.utils.knowledge_manager import KnowledgeManager
from app.utils.context_analyzer import ContextAnalyzer
from app.services.agent_service import get_agent_tools, initialize_agent_from_db
from app.utils.logger import (
    workflow_logger,
    workflow_decision_logger,
)

class AgentCoordinator:
    """Coordinates agent assignments and interactions."""
    
    def __init__(self):
        """Initialize coordinator."""
        self.db_conn = get_db_connection()
        self.knowledge_manager = KnowledgeManager()
        self.context_analyzer = ContextAnalyzer()

    def assign_tasks(self, team: Team, task: TeamTask, 
                    decomposition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assign decomposed tasks to appropriate agents.
        
        Args:
            team: The team to assign tasks to
            task: The parent task
            decomposition: Task decomposition details
            
        Returns:
            Dictionary containing task assignments
        """
        try:
            # Get team agents with capabilities
            team_agents = self._get_team_agents(team.team_id)
            workflow_logger.info("[WORKFLOW] Retrieved team agents", extra={
                'task_id': task.task_id,
                'team_id': team.team_id,
                'task_type': task.task_type,
                'agent_count': len(team_agents)
            })
            
            # Get context analysis
            context = self.context_analyzer.analyze(task, team)
            workflow_logger.info("[WORKFLOW] Retrieved context analysis", extra={
                'task_id': task.task_id,
                'team_id': team.team_id,
                'task_type': task.task_type,
                'required_tools': context.get('required_tools', []),
                'dependencies': context.get('dependencies', [])
            })
            
            # Create assignments for each subtask
            assignments = []
            for subtask in decomposition['subtasks']:
                # Find best agents for subtask
                qualified_agents = self._find_qualified_agents(team_agents, subtask)
                workflow_logger.info(f"[WORKFLOW] Found {len(qualified_agents)} qualified agents for subtask", extra={
                    'task_id': task.task_id,
                    'team_id': team.team_id,
                    'task_type': task.task_type,
                    'subtask_id': subtask.get('id'),
                    'qualified_agents': [a['agent_id'] for a in qualified_agents]
                })
                
                # Get agent knowledge
                agent_knowledge = self._get_agent_knowledge(
                    qualified_agents,
                    subtask
                )
                workflow_logger.info("[WORKFLOW] Retrieved agent knowledge", extra={
                    'task_id': task.task_id,
                    'team_id': team.team_id,
                    'task_type': task.task_type,
                    'subtask_id': subtask.get('id'),
                    'knowledge_count': len(agent_knowledge)
                })
                
                # Create assignment
                assignment = self._create_assignment(team, task, subtask, qualified_agents)
                assignments.append(assignment)
            
            # Store assignments
            assignment_id = self._store_assignments(task.task_id, assignments)
            workflow_logger.info("[WORKFLOW] Stored task assignments", extra={
                'task_id': task.task_id,
                'team_id': team.team_id,
                'task_type': task.task_type,
                'assignment_id': assignment_id,
                'assignment_count': len(assignments)
            })
            
            return {
                'assignments': assignments,
                'assignment_id': assignment_id
            }
            
        except Exception as e:
            workflow_logger.error(f"Error assigning tasks: {str(e)}", exc_info=True)
            return {
                'assignments': [],
                'assignment_id': None
            }

    def _get_team_agents(self, team_id: int) -> List[Dict[str, Any]]:
        """Get team agents with their capabilities."""
        try:
            cursor = self.db_conn.cursor(dictionary=True)
            
            # Get team agents with their tools
            cursor.execute("""
                SELECT 
                    a.id as agent_id,
                    a.name,
                    a.memory_type,
                    a.foundation_model,
                    ta.priority,
                    GROUP_CONCAT(at.tool_id) as tools
                FROM agents a
                JOIN team_agents ta ON a.id = ta.agent_id
                LEFT JOIN agent_tools at ON a.id = at.agent_id
                WHERE ta.team_id = %s
                GROUP BY a.id, a.name, a.memory_type, a.foundation_model, ta.priority
                ORDER BY ta.priority DESC
            """, (team_id,))
            
            agents = cursor.fetchall()
            
            # Process tools string into list and add default values
            for agent in agents:
                if agent['tools']:
                    agent['tools'] = [int(tool_id) for tool_id in agent['tools'].split(',')]
                else:
                    agent['tools'] = []
                
                # Add default values for missing columns
                agent['accuracy'] = 0.8  # Default accuracy
                agent['success'] = 0.9   # Default success rate
            
            return agents
            
        except Exception as e:
            workflow_logger.error(f"Error getting team agents: {str(e)}", exc_info=True)
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()

    def _find_qualified_agents(self, team_agents: List[Dict[str, Any]], 
                             subtask: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find agents qualified for a subtask."""
        try:
            qualified_agents = []
            required_tools = subtask.get('required_tools', [])
            
            for agent in team_agents:
                agent_tools = agent.get('tools', [])
                
                # Check if agent has required tools
                if all(tool['tool_id'] in agent_tools for tool in required_tools):
                    qualified_agents.append(agent)
            
            return qualified_agents
            
        except Exception as e:
            workflow_logger.error(f"Error finding qualified agents: {str(e)}", exc_info=True)
            return []

    def _get_agent_knowledge(self, agents: List[Dict[str, Any]], 
                           subtask: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant knowledge for agents."""
        try:
            knowledge_list = []
            
            for agent in agents:
                # Get agent's knowledge
                knowledge = self.knowledge_manager.get_relevant_knowledge(
                    agent['agent_id'],
                    subtask
                )
                
                if knowledge and knowledge.get('memories'):
                    knowledge_list.append({
                        'agent_id': agent['agent_id'],
                        'memories': knowledge['memories'],
                        'source_counts': knowledge.get('source_counts', {})
                    })
            
            return knowledge_list
            
        except Exception as e:
            workflow_logger.error(f"Error getting agent knowledge: {str(e)}", exc_info=True)
            return []

    def _create_assignment(self, team: Team, task: TeamTask, 
                         subtask: Dict[str, Any],
                         qualified_agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create task assignment."""
        try:
            return {
                'subtask_id': subtask['id'],
                'task_id': task.task_id,
                'team_id': team.team_id,
                'assigned_agents': [
                    {
                        'agent_id': agent['agent_id'],
                        'name': agent['name'],
                        'priority': agent.get('priority', 1),
                        'tools': agent.get('tools', [])
                    }
                    for agent in qualified_agents
                ],
                'required_tools': subtask.get('required_tools', []),
                'dependencies': subtask.get('dependencies', []),
                'estimated_time': subtask.get('estimated_time', 0),
                'complexity': subtask.get('complexity', 0.5),
                'confidence': subtask.get('confidence', 0.7)
            }
            
        except Exception as e:
            workflow_logger.error(f"Error creating assignment: {str(e)}", exc_info=True)
            return {}

    def _store_assignments(self, task_id: int, assignments: List[Dict[str, Any]]) -> Optional[int]:
        """Store task assignments in database."""
        try:
            cursor = self.db_conn.cursor()
            
            # Store assignments
            cursor.execute("""
                INSERT INTO task_assignments (
                    task_id,
                    assignments,
                    created_at
                ) VALUES (%s, %s, NOW())
            """, (
                task_id,
                json.dumps(assignments)
            ))
            
            assignment_id = cursor.lastrowid
            self.db_conn.commit()
            
            return assignment_id
            
        except Exception as e:
            workflow_logger.error(f"Error storing assignments: {str(e)}", exc_info=True)
            return None
        finally:
            if 'cursor' in locals():
                cursor.close()

    def get_assignment(self, assignment_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve stored task assignment."""
        conn = self.db_conn
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT task_id, assignments
                FROM task_assignments
                WHERE id = %s
            """, (assignment_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'task_id': row[0],
                'assignments': json.loads(row[1])
            }
            
        finally:
            cursor.close()
            conn.close()

    def update_agent_metrics(self, agent_id: int, task_result: Dict[str, Any]) -> None:
        """Update agent metrics based on task execution result."""
        conn = self.db_conn
        cursor = conn.cursor()
        
        try:
            # Update agent accuracy and success rates
            success = task_result.get('status') == 'success'
            accuracy = task_result.get('accuracy', 0.0)
            
            cursor.execute("""
                UPDATE agents
                SET accuracy_rate = (accuracy_rate + %s) / 2,
                    success_rate = CASE 
                        WHEN %s THEN (success_rate + 1) / 2
                        ELSE (success_rate + 0) / 2
                    END
                WHERE id = %s
            """, (accuracy, success, agent_id))
            
            conn.commit()
            
        finally:
            cursor.close()
            conn.close()

    def _match_agents_to_subtask(self, subtask: Dict[str, Any], available_agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Match agents to a subtask based on capabilities and requirements."""
        matched_agents = []
        required_tools = subtask.get('requirements', {}).get('tools', [])
        
        for agent in available_agents:
            agent_tools = [tool['name'].lower() for tool in agent.get('capabilities', {}).get('tools', [])]
            tool_match = any(tool.lower() in agent_tools for tool in required_tools)
            
            if tool_match:
                matched_agents.append({
                    'agent_id': agent['agent_id'],
                    'name': agent['name'],
                    'qualification_score': agent.get('accuracy', 0) * 0.6 + agent.get('success_rate', 0) * 0.4,
                    'tool_match': True
                })
        
        # Sort by qualification score
        matched_agents.sort(key=lambda x: x['qualification_score'], reverse=True)
        
        # Return top 3 matches
        return matched_agents[:3] 