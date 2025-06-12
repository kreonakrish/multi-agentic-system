"""Agent coordinator for managing agent collaboration and task assignment."""
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
from app.models.team import Team, TeamTask
from app.utils.db import get_db_connection
from app.utils.knowledge_manager import KnowledgeManager
from app.utils.context_analyzer import ContextAnalyzer
from app.services.agent_service import get_agent_tools, initialize_agent_from_db

logger = logging.getLogger(__name__)

class AgentCoordinator:
    """Coordinates agent assignments and interactions."""
    
    def __init__(self):
        """Initialize coordinator."""
        self.db_conn = get_db_connection()
        self.knowledge_manager = KnowledgeManager()
        self.context_analyzer = ContextAnalyzer()
        self.logger = logging.getLogger(__name__)

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
            
            # Get context analysis
            context = self.context_analyzer.analyze(task, team)
            
            # Create assignments for each subtask
            assignments = []
            for subtask in decomposition['subtasks']:
                # Find best agents for subtask
                qualified_agents = self._find_qualified_agents(team_agents, subtask)
                
                # Get agent knowledge
                agent_knowledge = self._get_agent_knowledge(
                    qualified_agents,
                    subtask
                )
                
                # Create assignment
                assignment = self._create_assignment(team, task, subtask, qualified_agents)
                
                assignments.append(assignment)
            
            # Store assignments
            assignment_id = self._store_assignments(task.task_id, assignments)
            
            return {
                'status': 'success',
                'assignment_id': assignment_id,
                'assignments': assignments
            }
            
        except Exception as e:
            self.logger.error(f"Error in task assignment: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    def _get_team_agents(self, team_id: int) -> List[Dict[str, Any]]:
        """Get team agents with their capabilities."""
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("""
                SELECT a.id, a.name, a.accuracy_rate, a.success_rate, a.priority
                FROM agents a
                JOIN team_agents ta ON a.id = ta.agent_id
                WHERE ta.team_id = %s
            """, (team_id,))
            
            agents = []
            for row in cursor.fetchall():
                agent_id, name, accuracy, success_rate, priority = row
                capabilities = self._get_agent_capabilities(agent_id)
                agents.append({
                    'agent_id': agent_id,
                    'name': name,
                    'accuracy': float(accuracy) if accuracy else 0.0,
                    'success_rate': float(success_rate) if success_rate else 0.0,
                    'priority': priority or 1,
                    'capabilities': capabilities
                })
            return agents
            
        except Exception as e:
            self.logger.error(f"Error getting team agents: {str(e)}")
            return []
        finally:
            cursor.close()

    def _get_agent_capabilities(self, agent_id: int) -> Dict[str, Any]:
        """Get agent capabilities from memory and performance history."""
        cursor = self.db_conn.cursor()
        try:
            cursor.execute("""
                SELECT t.tool_name, t.tool_type
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = %s
            """, (agent_id,))
            
            tools = [{'name': row[0], 'type': row[1]} for row in cursor.fetchall()]
            
            return {
                'tools': tools,
                'tool_count': len(tools)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting agent capabilities: {str(e)}")
            return {'tools': [], 'tool_count': 0}
        finally:
            cursor.close()

    def _find_qualified_agents(self, team_agents: List[Dict[str, Any]], subtask: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find agents qualified for a subtask based on their tools and capabilities."""
        qualified_agents = []
        required_tools = set(subtask.get('requirements', {}).get('tools', []))
        
        for agent in team_agents:
            # Get agent tools from service
            agent_tools_response = get_agent_tools(agent['agent_id'])
            if agent_tools_response.get('status') != 'success':
                continue
            
            # Extract tool names from the response
            agent_tools = set(
                tool['tool_name'].lower() 
                for tool in agent_tools_response.get('tools', [])
            )
            
            # Check if agent has required tools
            if required_tools and not required_tools.issubset(agent_tools):
                continue
            
            # Calculate qualification score
            qualification_score = agent.get('accuracy', 0) * 0.6 + agent.get('success_rate', 0) * 0.4
            
            qualified_agents.append({
                'agent_id': agent['agent_id'],
                'qualification_score': qualification_score,
                'tools': list(agent_tools)
            })
        
        # Sort by qualification score
        return sorted(qualified_agents, key=lambda x: x['qualification_score'], reverse=True)

    def _calculate_success_rate(self, capabilities: Dict[str, Any], 
                             subtask: Dict[str, Any]) -> float:
        """Calculate success rate for a subtask based on agent capabilities."""
        success_rate = 0.0
        
        # Check if agent has required tools
        required_tools = set(subtask.get('requirements', {}).get('tools', []))
        if not required_tools.issubset(set(capabilities['tools'].keys())):
            return success_rate
        
        # Calculate success rate based on tool usage
        for tool in required_tools:
            tool_stats = capabilities['tools'][tool]
            success_rate += tool_stats['success_rate'] * 0.2
        
        return min(success_rate, 1.0)

    def _get_agent_knowledge(self, qualified_agents: List[Dict[str, Any]], 
                           subtask: Dict[str, Any]) -> Dict[str, Any]:
        """Get relevant knowledge for qualified agents."""
        knowledge = {}
        
        for qual_agent in qualified_agents:
            agent_id = qual_agent['agent_id']
            
            # Create subtask as TeamTask for knowledge retrieval
            subtask_as_task = TeamTask(
                task_id=subtask['subtask_id'],
                description=subtask['description'],
                requirements=subtask['requirements']
            )
            
            # Get relevant knowledge
            agent_knowledge = self.knowledge_manager.get_relevant_knowledge(
                agent_id,
                subtask_as_task
            )
            
            knowledge[agent_id] = {
                'relevant_memories': agent_knowledge['memories'],
                'memory_counts': agent_knowledge['source_counts']
            }
        
        return knowledge

    def _create_assignment(self, team: Team, task: TeamTask, subtask: Dict[str, Any], available_agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an assignment for a subtask."""
        try:
            # Extract or set default priority
            priority = subtask.get('priority', 1)
            
            # Get the best matching agents for the subtask
            matched_agents = self._match_agents_to_subtask(subtask, available_agents)
            
            if not matched_agents:
                return {
                    'status': 'error',
                    'error': f'No qualified agents found for subtask {subtask.get("subtask_id")}',
                    'subtask_id': subtask.get('subtask_id')
                }

            # Create the assignment record
            cursor = self.db_conn.cursor()
            try:
                assignment_data = {
                    'subtask_id': subtask.get('subtask_id'),
                    'priority': priority,
                    'assigned_agents': matched_agents
                }
                
                cursor.execute("""
                    INSERT INTO task_assignments (task_id, assignments)
                    VALUES (%s, %s)
                """, (task.task_id, json.dumps(assignment_data)))
                
                assignment_id = cursor.lastrowid
                self.db_conn.commit()
                
                return {
                    'status': 'success',
                    'assignment_id': assignment_id,
                    'subtask_id': subtask.get('subtask_id'),
                    'assigned_agents': matched_agents
                }
                
            except Exception as e:
                self.logger.error(f"Database error in assignment creation: {str(e)}")
                self.db_conn.rollback()
                return {
                    'status': 'error',
                    'error': str(e),
                    'subtask_id': subtask.get('subtask_id')
                }
            finally:
                cursor.close()
                
        except Exception as e:
            self.logger.error(f"Error in assignment creation: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'subtask_id': subtask.get('subtask_id')
            }

    def _store_assignments(self, task_id: str, assignments: List[Dict[str, Any]]) -> int:
        """Store task assignments in database."""
        cursor = self.db_conn.cursor()
        try:
            # Store assignments as JSON
            cursor.execute("""
                INSERT INTO task_assignments (task_id, assignments)
                VALUES (%s, %s)
            """, (task_id, json.dumps(assignments)))
            
            assignment_id = cursor.lastrowid
            self.db_conn.commit()
            return assignment_id
            
        except Exception as e:
            self.logger.error(f"Error storing assignments: {str(e)}")
            self.db_conn.rollback()
            raise
        finally:
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