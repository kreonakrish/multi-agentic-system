"""Task decomposer for breaking down complex tasks."""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime
from app.utils.db import get_db_connection, safe_close_connection
from app.models.task import TeamTask
from app.utils.context_analyzer import ContextAnalyzer
from collections import defaultdict
from app.utils.json_encoder import CustomJSONEncoder
from app.utils.logger import (
    workflow_logger,
    workflow_decision_logger,
)
import uuid


class TaskDecomposer:
    def __init__(self):
        self.context_analyzer = ContextAnalyzer()
        self.db_conn = get_db_connection()

    def decompose(self, task: TeamTask, context_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Decompose a task into subtasks and their dependencies."""
        try:
            workflow_logger.info("[WORKFLOW] Starting task decomposition", extra={
                'task_id': task.task_id,
                'task_type': task.task_type,
                'complexity': task.complexity,
                'priority': task.priority
            })
            
            # Extract team_id from task requirements
            team_id = task.requirements.get('team_id')
            if not team_id and isinstance(task.requirements.get('context'), dict):
                team_id = task.requirements['context'].get('team_id')
            
            if not team_id:
                raise ValueError("team_id is required but not found in task requirements")

            # First, ensure the task exists in team_tasks
            cursor = self.db_conn.cursor()
            try:
                # Check if task already exists
                cursor.execute("""
                    SELECT task_id FROM team_tasks 
                    WHERE task_id = %s
                """, (task.task_id,))
                
                existing_task = cursor.fetchone()
                if not existing_task:
                    # Only insert if task doesn't exist
                    cursor.execute("""
                        INSERT INTO team_tasks (
                            task_id, 
                            team_id,
                            description, 
                            requirements,
                            status,
                            priority,
                            created_at,
                            updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        task.task_id,
                        team_id,
                        task.description,
                        json.dumps(task.requirements),
                        'pending',
                        1
                    ))
                    self.db_conn.commit()

                # Now proceed with task decomposition
                subtasks = self._create_subtasks(task, context_analysis)
                
                # Ensure each subtask has a priority
                for subtask in subtasks:
                    if 'priority' not in subtask:
                        subtask['priority'] = 1
                        
                dependencies = self._determine_dependencies(subtasks)
                execution_plan = self._create_execution_plan(subtasks, dependencies)
                
                # Store the decomposition
                cursor.execute("""
                    INSERT INTO task_decompositions (
                        task_id, 
                        subtasks, 
                        dependencies, 
                        execution_plan,
                        created_at,
                        updated_at
                    ) VALUES (%s, %s, %s, %s, NOW(), NOW())
                """, (
                    task.task_id,
                    json.dumps(subtasks),
                    json.dumps(dependencies),
                    json.dumps(execution_plan)
                ))
                decomposition_id = cursor.lastrowid
                self.db_conn.commit()
                
                # Log decomposition decisions
                workflow_decision_logger.info("[DECISION] Task decomposition completed", extra={
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'strategy': 'manual',
                    'subtask_count': len(subtasks),
                    'dependency_count': len(dependencies),
                    'parallel_group_count': len(execution_plan['parallel_groups']),
                    'critical_path_length': len(execution_plan['critical_path']),
                    'complexity_score': self._calculate_complexity_score(subtasks, dependencies)
                })
                
                return {
                    'status': 'success',
                    'task_id': task.task_id,
                    'decomposition_id': decomposition_id,
                    'subtasks': subtasks,
                    'dependencies': dependencies,
                    'execution_plan': execution_plan
                }
                
            except Exception as e:
                workflow_logger.error(f"Error storing decomposition: {str(e)}", exc_info=True, extra={
                    'task_id': task.task_id,
                    'task_type': task.task_type,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                # Rollback any failed transaction
                self.db_conn.rollback()
                return {
                    'status': 'error',
                    'error': str(e),
                    'task_id': task.task_id,
                    'decomposition_id': None,
                    'subtasks': [],
                    'dependencies': [],
                    'execution_plan': {
                        'parallel_groups': [],
                        'dependencies': [],
                        'critical_path': [],
                        'estimated_time': 0
                    }
                }
            finally:
                cursor.close()
                
        except Exception as e:
            workflow_logger.error(f"Critical error in task decomposition: {str(e)}", exc_info=True, extra={
                'task_id': task.task_id,
                'task_type': task.task_type,
                'error': str(e),
                'error_type': type(e).__name__
            })
            return {
                'status': 'error',
                'error': str(e),
                'task_id': task.task_id,
                'decomposition_id': None,
                'subtasks': [],
                'dependencies': [],
                'execution_plan': {
                    'parallel_groups': [],
                    'dependencies': [],
                    'critical_path': [],
                    'estimated_time': 0
                }
            }

    def _decompose_task(self, task: TeamTask) -> Dict[str, Any]:
        """Internal method to decompose a task into subtasks and their relationships."""
        # Get context analysis
        context_analysis = self.context_analyzer.analyze(task)
        
        # Create subtasks based on requirements
        subtasks = self._create_subtasks(task, context_analysis)
        
        # Determine dependencies between subtasks
        dependencies = self._determine_dependencies(subtasks)

        # Create execution plan
        execution_plan = self._create_execution_plan(subtasks, dependencies)
        
        return {
            'task_id': task.task_id,
            'subtasks': subtasks,
            'dependencies': dependencies,
            'execution_plan': execution_plan
        }

    def _create_subtasks(self, task: TeamTask, context_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create subtasks based on task and context analysis."""
        try:
            subtasks = []
            
            # Get required tools and dependencies
            required_tools = context_analysis.get('required_tools', [])
            dependencies = context_analysis.get('dependencies', [])
            
            # Check if this is a predefined task
            if task.task_type == 'predefined':
                # For predefined tasks, create a single subtask
                subtasks.append({
                    'id': str(uuid.uuid4()),
                    'name': f"Execute {task.task_type} task",
                    'description': task.description,
                    'type': task.task_type,
                    'priority': 'high',
                    'dependencies': [],
                    'required_tools': required_tools,
                    'estimated_time': 5,  # Default time for predefined tasks
                    'complexity': context_analysis.get('complexity_score', 0.5),
                    'confidence': context_analysis.get('confidence_score', 0.7)
                })
                return subtasks
            
            # For non-predefined tasks, analyze requirements
            needs_database = any(tool['tool_type'] == 'Database' for tool in required_tools)
            needs_api = any(tool['tool_type'] == 'APIService' for tool in required_tools)
            needs_pipeline = any(tool['tool_type'] in ['WebService', 'APIService'] for tool in required_tools)
            
            # Create subtasks based on requirements
            if needs_database:
                subtasks.append({
                    'id': str(uuid.uuid4()),
                    'name': 'Database Operations',
                    'description': 'Perform database operations',
                    'type': 'database',
                    'priority': 'high',
                    'dependencies': [],
                    'required_tools': [tool for tool in required_tools if tool['tool_type'] == 'Database'],
                    'estimated_time': 10,
                    'complexity': context_analysis.get('complexity_score', 0.5),
                    'confidence': context_analysis.get('confidence_score', 0.7)
                })
            
            if needs_api:
                subtasks.append({
                    'id': str(uuid.uuid4()),
                    'name': 'API Integration',
                    'description': 'Handle API integration tasks',
                    'type': 'api',
                    'priority': 'high',
                    'dependencies': [],
                    'required_tools': [tool for tool in required_tools if tool['tool_type'] == 'APIService'],
                    'estimated_time': 15,
                    'complexity': context_analysis.get('complexity_score', 0.5),
                    'confidence': context_analysis.get('confidence_score', 0.7)
                })
            
            if needs_pipeline:
                subtasks.append({
                    'id': str(uuid.uuid4()),
                    'name': 'Pipeline Processing',
                    'description': 'Process pipeline operations',
                    'type': 'pipeline',
                    'priority': 'high',
                    'dependencies': [],
                    'required_tools': [tool for tool in required_tools if tool['tool_type'] in ['WebService', 'APIService']],
                    'estimated_time': 20,
                    'complexity': context_analysis.get('complexity_score', 0.5),
                    'confidence': context_analysis.get('confidence_score', 0.7)
                })
            
            # If no specific subtasks were created, create a general task
            if not subtasks:
                subtasks.append({
                    'id': str(uuid.uuid4()),
                    'name': 'General Task',
                    'description': task.description,
                    'type': 'general',
                    'priority': 'medium',
                    'dependencies': [],
                    'required_tools': required_tools,
                    'estimated_time': 10,
                    'complexity': context_analysis.get('complexity_score', 0.5),
                    'confidence': context_analysis.get('confidence_score', 0.7)
                })
            
            # Update dependencies between subtasks
            for i in range(1, len(subtasks)):
                subtasks[i]['dependencies'].append(subtasks[i-1]['id'])
            
            return subtasks
            
        except Exception as e:
            workflow_logger.error(f"Error creating subtasks: {str(e)}", exc_info=True)
            return []

    def _determine_dependencies(self, subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Determine dependencies between subtasks."""
        dependencies = []
        
        # Find data preparation subtask
        data_prep_task = next(
            (task for task in subtasks if task['type'] == 'data_preparation'),
            None
        )
        
        # Find pipeline tasks
        pipeline_tasks = [
            task for task in subtasks 
            if 'pipeline' in task['type'].lower()
        ]
        
        # Add dependencies from data preparation to pipeline tasks
        if data_prep_task:
            for pipeline_task in pipeline_tasks:
                dependencies.append({
                    'from_id': data_prep_task['id'],
                    'to_id': pipeline_task['id'],
                    'type': 'sequential',
                    'critical': True
                })
        
        # Find validation task
        validation_task = next(
            (task for task in subtasks if task['type'] == 'validation'),
            None
        )
        
        # Add dependencies from pipeline tasks to validation
        if validation_task:
            for pipeline_task in pipeline_tasks:
                dependencies.append({
                    'from_id': pipeline_task['id'],
                    'to_id': validation_task['id'],
                    'type': 'sequential',
                    'critical': True
                })
        
        # Find result compilation task
        result_task = next(
            (task for task in subtasks if task['type'] == 'result_compilation'),
            None
        )
        
        # Add dependencies to result compilation
        if result_task:
            for task in subtasks:
                if task['id'] != result_task['id']:
                    dependencies.append({
                        'from_id': task['id'],
                        'to_id': result_task['id'],
                        'type': 'sequential',
                        'critical': False
                    })
        
        return dependencies

    def _create_execution_plan(self, subtasks: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create execution plan with parallel and sequential steps."""
        try:
            # Create dependency graph
            graph = {}
            for task in subtasks:
                graph[task['id']] = set()
            
            # Add dependencies to graph
            for dep in dependencies:
                source = dep['from_id']
                target = dep['to_id']
                if source in graph and target in graph:
                    graph[source].add(target)
            
            # Find parallel execution groups
            parallel_groups = []
            visited = set()
            
            def dfs(node, current_group):
                visited.add(node)
                current_group.append(node)
                
                # Check all dependencies
                for dep in graph[node]:
                    if dep not in visited:
                        dfs(dep, current_group)
            
            # Find all connected components
            for node in graph:
                if node not in visited:
                    current_group = []
                    dfs(node, current_group)
                    parallel_groups.append(current_group)
            
            # Create execution plan
            execution_plan = {
                'parallel_groups': parallel_groups,
                'dependencies': dependencies,
                'critical_path': self._find_critical_path(graph),
                'estimated_time': self._calculate_estimated_time(subtasks, parallel_groups)
            }
            
            workflow_logger.info("[WORKFLOW] Created execution plan", extra={
                'parallel_groups': len(parallel_groups),
                'dependencies': len(dependencies),
                'estimated_time': execution_plan['estimated_time']
            })
            
            return execution_plan
            
        except Exception as e:
            workflow_logger.error(f"Error creating execution plan: {str(e)}", exc_info=True)
            return {
                'parallel_groups': [],
                'dependencies': [],
                'critical_path': [],
                'estimated_time': 0
            }

    def _find_critical_path(self, graph: Dict[str, set]) -> List[str]:
        """Find critical path in the dependency graph."""
        try:
            # Calculate in-degree for each node
            in_degree = {node: 0 for node in graph}
            for node in graph:
                for dep in graph[node]:
                    in_degree[dep] += 1
            
            # Find nodes with no incoming edges
            queue = [node for node, degree in in_degree.items() if degree == 0]
            critical_path = []
            
            while queue:
                node = queue.pop(0)
                critical_path.append(node)
                
                # Update in-degree for dependencies
                for dep in graph[node]:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
            
            return critical_path
            
        except Exception as e:
            workflow_logger.error(f"Error finding critical path: {str(e)}", exc_info=True)
            return []

    def _calculate_estimated_time(self, subtasks: List[Dict[str, Any]], parallel_groups: List[List[str]]) -> int:
        """Calculate estimated execution time."""
        try:
            # Create subtask lookup
            subtask_lookup = {task['id']: task for task in subtasks}
            
            # Calculate time for each parallel group
            group_times = []
            for group in parallel_groups:
                # Time for parallel group is max time of any subtask in the group
                group_time = max(
                    subtask_lookup[task_id]['estimated_time']
                    for task_id in group
                    if task_id in subtask_lookup
                )
                group_times.append(group_time)
            
            # Total time is sum of all group times
            return sum(group_times)
            
        except Exception as e:
            workflow_logger.error(f"Error calculating estimated time: {str(e)}", exc_info=True)
            return 0

    def _store_decomposition(self, task: TeamTask, subtasks: List[Dict[str, Any]],
                           dependencies: List[Dict[str, Any]], 
                           execution_plan: List[Dict[str, Any]]) -> int:
        """Store task decomposition in database."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Store decomposition record
            cursor.execute("""
                INSERT INTO task_decompositions (
                    task_id,
                    subtasks,
                    dependencies,
                    execution_plan,
                    created_at
                ) VALUES (
                    %s, %s, %s, %s, NOW()
                )
            """, (
                task.task_id,
                json.dumps(subtasks),
                json.dumps(dependencies),
                json.dumps(execution_plan)
            ))
            
            decomposition_id = cursor.lastrowid
            conn.commit()
            return decomposition_id
            
        finally:
            cursor.close()
            conn.close()

    def get_decomposition(self, decomposition_id: int) -> Dict[str, Any]:
        """Retrieve a stored task decomposition."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT parent_task_id, subtasks, dependencies, execution_plan
                FROM task_decomposition
                WHERE id = %s
            """, (decomposition_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'parent_task_id': row[0],
                'subtasks': json.loads(row[1]),
                'dependencies': json.loads(row[2]),
                'execution_plan': json.loads(row[3])
            }
            
        finally:
            cursor.close()
            conn.close()

    def _get_critical_path(self, dependencies: List[Dict[str, Any]]) -> List[str]:
        """Calculate the critical path from dependencies."""
        # Create a graph representation
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Build the graph
        for dep in dependencies:
            source = dep['from_id']
            target = dep['to_id']
            graph[source].append(target)
            in_degree[target] += 1
            
        # Find start nodes (nodes with no incoming edges)
        start_nodes = [node for node in graph if in_degree[node] == 0]
        
        # If no start nodes found, return empty list
        if not start_nodes:
            return []
            
        # Use topological sort to find critical path
        critical_path = []
        queue = start_nodes
        
        while queue:
            node = queue.pop(0)
            critical_path.append(node)
            
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        return critical_path 

    def _calculate_complexity_score(self, subtasks: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> float:
        """Calculate complexity score based on subtasks and dependencies."""
        # Base complexity from number of subtasks
        base_complexity = len(subtasks) * 0.2
        
        # Add complexity from dependencies
        dependency_complexity = len(dependencies) * 0.1
        
        # Add complexity from critical dependencies
        critical_deps = sum(1 for dep in dependencies if dep.get('critical', False))
        critical_complexity = critical_deps * 0.3
        
        # Add complexity from task types
        type_complexity = 0
        for subtask in subtasks:
            if subtask.get('estimated_complexity') == 'high':
                type_complexity += 0.5
            elif subtask.get('estimated_complexity') == 'medium':
                type_complexity += 0.3
            elif subtask.get('estimated_complexity') == 'low':
                type_complexity += 0.1
        
        # Calculate total complexity score (normalized between 0 and 1)
        total_complexity = base_complexity + dependency_complexity + critical_complexity + type_complexity
        normalized_complexity = min(1.0, total_complexity / 5.0)  # Normalize to max of 1.0
        
        return round(normalized_complexity, 2) 