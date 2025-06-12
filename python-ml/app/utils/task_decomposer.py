"""Task decomposer for breaking down complex tasks."""
from typing import Dict, Any, List
import json
import logging
from datetime import datetime
from app.utils.db import get_db_connection, safe_close_connection
from app.models.task import TeamTask
from app.utils.context_analyzer import ContextAnalyzer
from collections import defaultdict
from app.utils.json_encoder import CustomJSONEncoder

logger = logging.getLogger(__name__)

class TaskDecomposer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.context_analyzer = ContextAnalyzer()
        self.db_conn = get_db_connection()

    def decompose(self, task: TeamTask, context_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Decompose a task into subtasks and their dependencies."""
        try:
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
                
                return {
                    'status': 'success',
                    'task_id': task.task_id,
                    'decomposition_id': decomposition_id,
                    'subtasks': subtasks,
                    'dependencies': dependencies,
                    'execution_plan': execution_plan
                }
                
            except Exception as e:
                self.logger.error(f"Error storing decomposition: {str(e)}")
                # Rollback any failed transaction
                self.db_conn.rollback()
                return {
                    'status': 'error',
                    'error': str(e),
                    'task_id': task.task_id,
                    'decomposition_id': None,
                    'subtasks': [],
                    'dependencies': [],
                    'execution_plan': []
                }
            finally:
                cursor.close()
                
        except Exception as e:
            self.logger.error(f"Critical error in task decomposition: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'task_id': task.task_id,
                'decomposition_id': None,
                'subtasks': [],
                'dependencies': [],
                'execution_plan': []
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
        """Create atomic subtasks based on task requirements."""
        subtasks = []
        
        # Get pipeline requirements
        needs_pipeline = context_analysis['explicit_requirements'].get('needs_pipeline', False)
        pipeline_types = context_analysis['explicit_requirements'].get('pipeline_type', [])
        
        # Add pipeline creation subtasks
        if needs_pipeline:
            for pipeline_type in pipeline_types:
                subtask_id = f"sub-{len(subtasks) + 1}"
                subtasks.append({
                    'subtask_id': subtask_id,
                    'type': pipeline_type,
                    'description': f"Create {pipeline_type.replace('_', ' ')}",
                    'requirements': {'tools': [pipeline_type.split('_')[0].lower()]},
                    'priority': 1,
                    'estimated_complexity': 'high'
                })
        
        # Add data preparation subtask
        if context_analysis['implicit_requirements'].get('data_processing'):
            subtask_id = f"sub-{len(subtasks) + 1}"
            subtasks.append({
                'subtask_id': subtask_id,
                'type': 'data_preparation',
                'description': 'Prepare and validate input data',
                'requirements': {'tools': ['database', 'data_processing']},
                'priority': 2,
                'estimated_complexity': 'medium'
            })
        
        # Add validation subtask
        if context_analysis['implicit_requirements'].get('needs_validation'):
            subtask_id = f"sub-{len(subtasks) + 1}"
            subtasks.append({
                'subtask_id': subtask_id,
                'type': 'validation',
                'description': 'Validate results and ensure quality',
                'requirements': {'tools': ['validation_engine']},
                'priority': 3,
                'estimated_complexity': 'medium'
            })
        
        # Add result compilation subtask
        subtask_id = f"sub-{len(subtasks) + 1}"
        subtasks.append({
            'subtask_id': subtask_id,
            'type': 'result_compilation',
            'description': 'Compile and format final results',
            'requirements': {'tools': ['result_formatter']},
            'priority': 4,
            'estimated_complexity': 'low'
        })
        
        return subtasks

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
                    'from_id': data_prep_task['subtask_id'],
                    'to_id': pipeline_task['subtask_id'],
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
                    'from_id': pipeline_task['subtask_id'],
                    'to_id': validation_task['subtask_id'],
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
                if task['subtask_id'] != result_task['subtask_id']:
                    dependencies.append({
                        'from_id': task['subtask_id'],
                        'to_id': result_task['subtask_id'],
                        'type': 'sequential',
                        'critical': False
                    })
        
        return dependencies

    def _create_execution_plan(self, subtasks: List[Dict[str, Any]], 
                             dependencies: List[Dict[str, Any]]) -> List[List[str]]:
        """Create execution plan based on dependencies."""
        # Create dependency graph
        graph = {}
        for task in subtasks:
            graph[task['subtask_id']] = set()
        
        for dep in dependencies:
            if dep['from_id'] in graph and dep['to_id'] in graph:
                graph[dep['to_id']].add(dep['from_id'])
        
        # Find tasks with no dependencies
        no_deps = [
            task_id for task_id in graph 
            if not graph[task_id]
        ]
        
        # Create execution plan
        execution_plan = []
        executed = set()
        
        while no_deps:
            execution_plan.append(no_deps[:])
            executed.update(no_deps)
            
            # Find next level of tasks
            next_level = []
            for task_id in graph:
                if task_id not in executed:
                    deps = graph[task_id]
                    if all(dep in executed for dep in deps):
                        next_level.append(task_id)
            
            no_deps = next_level
        
        return execution_plan

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