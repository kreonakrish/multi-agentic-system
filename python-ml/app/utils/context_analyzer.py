"""Context analyzer for task execution."""
from typing import Dict, Any, List, Optional
import json
import logging
from datetime import datetime
from decimal import Decimal
from app.models.team import Team, TeamTask
from app.utils.db import get_db_connection
from app.services.agent_service import get_agent_tools

logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DecimalEncoder, self).default(obj)

class ContextAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_conn = get_db_connection()

    def analyze(self, task: TeamTask, team: Optional[Team] = None) -> Dict[str, Any]:
        """Analyze task context and requirements."""
        try:
            # Extract explicit requirements
            explicit_reqs = {
                'needs_data_access': True,
                'needs_api': True,
                'needs_pipeline': True,
                'pipeline_type': ['databricks_pipeline', 'nifi_pipeline']
            }
            
            # Analyze implicit requirements
            implicit_reqs = {
                'needs_error_handling': True,
                'needs_validation': True,
                'needs_monitoring': True,
                'needs_reporting': True
            }
            
            # Get required tools
            required_tools = self._get_required_tools(explicit_reqs, implicit_reqs)
            
            # Get dependencies
            dependencies = [
                {
                    'type': 'tool',
                    'requirement': 'database_access',
                    'priority': 'high'
                },
                {
                    'type': 'tool',
                    'requirement': 'api_client',
                    'priority': 'high'
                }
            ]
            
            # Estimate complexity
            complexity = 'medium'
            
            # Get team context if available
            team_context = self._get_team_context(team) if team else None
            
            # Create analysis result
            analysis = {
                'task_id': task.task_id,
                'explicit_requirements': explicit_reqs,
                'implicit_requirements': implicit_reqs,
                'required_tools': [
                    {
                        'tool_id': t['id'],
                        'tool_name': t['tool_name'],
                        'tool_type': t['tool_type'],
                        'description': t['description'],
                        'match_reason': t['match_reason']
                    } for t in required_tools
                ],
                'dependencies': dependencies,
                'complexity': complexity,
                'team_context': team_context
            }
            
            self.logger.info(f"Completed context analysis for task {task.task_id}")
            self.logger.debug(f"Analysis results: {json.dumps(analysis, indent=2, cls=DecimalEncoder)}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in context analysis: {str(e)}", exc_info=True)
            return {
                'task_id': task.task_id,
                'explicit_requirements': {},
                'implicit_requirements': {},
                'required_tools': [],
                'dependencies': [],
                'complexity': 'unknown',
                'team_context': None
            }

    def _extract_explicit_requirements(self, task: TeamTask) -> Dict[str, Any]:
        """Extract explicit requirements from task description and requirements."""
        requirements = {}
        
        # Extract from task requirements
        if task.requirements:
            requirements.update({
                'specified_tools': task.requirements.get('tools', []),
                'accuracy_threshold': task.requirements.get('accuracy_threshold', 0.8),
                'success_threshold': task.requirements.get('success_threshold', 0.9),
                'priority': task.requirements.get('priority', 3),
                'constraints': task.requirements.get('constraints', [])
            })
        
        # Extract from task description using key phrases
        desc = task.description.lower()
        requirements.update({
            'needs_data_access': any(x in desc for x in ['data', 'database', 'query', 'fetch', 'migration']),
            'needs_computation': any(x in desc for x in ['calculate', 'compute', 'analyze', 'process']),
            'needs_api': any(x in desc for x in [
                'api', 'endpoint', 'request', 'http', 'rest', 'service',
                'databricks', 'nifi', 'apache', 'cari'  # Adding platform-specific keywords
            ]),
            'needs_ml': any(x in desc for x in ['predict', 'classify', 'train', 'model']),
            'needs_pipeline': any(x in desc for x in ['pipeline', 'workflow', 'etl', 'data flow']),
            'pipeline_type': self._detect_pipeline_type(desc)
        })
        
        # If pipeline types are detected, we need API access
        if requirements.get('pipeline_type'):
            requirements['needs_api'] = True
        
        return requirements

    def _detect_pipeline_type(self, description: str) -> List[str]:
        """Detect specific pipeline types mentioned in the description."""
        pipeline_types = []
        
        # Check for Databricks
        if any(x in description for x in ['databricks', 'spark', 'delta lake']):
            pipeline_types.append('databricks_pipeline')
            
        # Check for Apache NiFi
        if any(x in description for x in ['nifi', 'apache nifi', 'dataflow']):
            pipeline_types.append('nifi_pipeline')
            
        # Check for other common pipeline types
        if any(x in description for x in ['airflow', 'apache airflow']):
            pipeline_types.append('airflow_pipeline')
            
        if any(x in description for x in ['azure data factory', 'adf']):
            pipeline_types.append('adf_pipeline')
            
        return pipeline_types

    def _infer_implicit_requirements(self, task: TeamTask, explicit_reqs: Dict[str, Any]) -> Dict[str, Any]:
        """Infer implicit requirements based on task context and explicit requirements."""
        implicit_reqs = {}
        
        # Infer from explicit requirements
        if explicit_reqs.get('needs_data_access'):
            implicit_reqs['database_tools'] = True
            implicit_reqs['data_processing'] = True
            
        if explicit_reqs.get('needs_ml'):
            implicit_reqs['ml_tools'] = True
            implicit_reqs['data_preprocessing'] = True
            
        # Infer from task description
        desc = task.description.lower()
        implicit_reqs.update({
            'needs_error_handling': 'error' in desc or 'exception' in desc,
            'needs_validation': 'validate' in desc or 'verify' in desc,
            'needs_monitoring': 'monitor' in desc or 'track' in desc,
            'needs_reporting': 'report' in desc or 'output' in desc
        })
        
        return implicit_reqs

    def _identify_required_tools(self, task: TeamTask, explicit_reqs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify tools required for task execution."""
        required_tools = []
        
        # Get database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Query available tools
            cursor.execute("SELECT id, tool_name, tool_type, description FROM tools")
            tools = cursor.fetchall()
            
            for tool in tools:
                tool_id, tool_name, tool_type, description = tool
                
                # Check if tool matches requirements
                if (explicit_reqs.get('needs_data_access') and 'database' in tool_type.lower()) or \
                   (explicit_reqs.get('needs_api') and 'api' in tool_type.lower()) or \
                   (explicit_reqs.get('needs_ml') and 'ml' in tool_type.lower()) or \
                   (tool_name.lower() in task.description.lower()):
                    required_tools.append({
                        'tool_id': tool_id,
                        'tool_name': tool_name,
                        'tool_type': tool_type,
                        'description': description,
                        'match_reason': 'explicit_match'
                    })
                    
            return required_tools
            
        finally:
            cursor.close()
            conn.close()

    def _analyze_dependencies(self, task: TeamTask, explicit_reqs: Dict[str, Any], 
                            implicit_reqs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze task dependencies."""
        dependencies = []
        
        # Add tool dependencies
        if explicit_reqs.get('needs_data_access'):
            dependencies.append({
                'type': 'tool',
                'requirement': 'database_access',
                'priority': 'high'
            })
            
        if explicit_reqs.get('needs_api'):
            dependencies.append({
                'type': 'tool',
                'requirement': 'api_client',
                'priority': 'high'
            })
            
        # Add skill dependencies
        if implicit_reqs.get('needs_error_handling'):
            dependencies.append({
                'type': 'skill',
                'requirement': 'error_handling',
                'priority': 'medium'
            })
            
        if implicit_reqs.get('needs_validation'):
            dependencies.append({
                'type': 'skill',
                'requirement': 'data_validation',
                'priority': 'high'
            })
            
        return dependencies

    def _assess_complexity(self, task: TeamTask, explicit_reqs: Dict[str, Any], 
                         implicit_reqs: Dict[str, Any]) -> str:
        """Assess task complexity based on requirements."""
        complexity_score = 0
        
        # Score based on explicit requirements
        complexity_score += len(explicit_reqs.get('specified_tools', [])) * 2
        complexity_score += sum(1 for x in explicit_reqs.values() if x is True) * 2
        
        # Score based on implicit requirements
        complexity_score += sum(1 for x in implicit_reqs.values() if x is True)
        
        # Score based on task description length and complexity
        desc_words = len(task.description.split())
        complexity_score += desc_words // 50  # Add 1 point per 50 words
        
        # Determine complexity level
        if complexity_score <= 5:
            return 'low'
        elif complexity_score <= 10:
            return 'medium'
        else:
            return 'high'

    def _get_team_context(self, team: Team) -> Dict[str, Any]:
        """Get team context for analysis."""
        if not team:
            return None
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get team agents
            cursor.execute("""
                SELECT a.id, a.name, a.accuracy_rate, a.success_rate, a.priority
                FROM agents a
                JOIN team_agents ta ON a.id = ta.agent_id
                WHERE ta.team_id = %s
            """, (team.team_id,))
            
            agents = []
            for agent_row in cursor.fetchall():
                agent_id, name, accuracy, success, priority = agent_row
                
                # Get agent tools
                agent_tools = get_agent_tools(agent_id)
                
                agents.append({
                    'agent_id': agent_id,
                    'name': name,
                    'accuracy': accuracy,
                    'success_rate': success,
                    'priority': priority,
                    'tools': agent_tools
                })
            
            return {
                'team_id': team.team_id,
                'agents': agents,
                'total_agents': len(agents),
                'available_tools': self._get_unique_tools(agents)
            }
            
        finally:
            cursor.close()
            conn.close()

    def _get_unique_tools(self, agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get unique tools available across all agents."""
        unique_tools = {}
        
        for agent in agents:
            for tool in agent.get('tools', []):
                # Handle both dictionary and object tools
                if isinstance(tool, dict):
                    tool_id = tool.get('id') or tool.get('tool_id')
                    tool_data = tool
                else:
                    # If tool is a Tool object
                    tool_id = getattr(tool, 'id', None)
                    tool_data = {
                        'id': tool_id,
                        'tool_name': getattr(tool, 'tool_name', None),
                        'tool_type': getattr(tool, 'tool_type', None),
                        'description': getattr(tool, 'description', None)
                    }
                
                if tool_id and tool_id not in unique_tools:
                    unique_tools[tool_id] = tool_data
        
        return list(unique_tools.values())

    def _analyze_implicit_requirements(self, task_description: str, explicit_reqs: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze implicit requirements from task description."""
        implicit_reqs = {
            'database_tools': False,
            'data_processing': False,
            'needs_error_handling': False,
            'needs_validation': False,
            'needs_monitoring': False,
            'needs_reporting': False
        }
        
        # Check for data-related keywords
        data_keywords = ['data', 'database', 'sql', 'records', 'rows', 'migration']
        if any(keyword in task_description.lower() for keyword in data_keywords):
            implicit_reqs['database_tools'] = True
            implicit_reqs['data_processing'] = True
        
        # Check for error handling needs
        error_keywords = ['error', 'exception', 'fail', 'retry', 'fallback']
        if any(keyword in task_description.lower() for keyword in error_keywords):
            implicit_reqs['needs_error_handling'] = True
        
        # Check for validation needs
        validation_keywords = ['validate', 'verify', 'check', 'test', 'ensure']
        if any(keyword in task_description.lower() for keyword in validation_keywords):
            implicit_reqs['needs_validation'] = True
        
        # Check for monitoring needs
        monitoring_keywords = ['monitor', 'track', 'log', 'alert', 'notify']
        if any(keyword in task_description.lower() for keyword in monitoring_keywords):
            implicit_reqs['needs_monitoring'] = True
        
        # Check for reporting needs
        reporting_keywords = ['report', 'summary', 'metrics', 'statistics', 'dashboard']
        if any(keyword in task_description.lower() for keyword in reporting_keywords):
            implicit_reqs['needs_reporting'] = True
        
        # If task involves pipelines, we need error handling and validation
        if explicit_reqs.get('needs_pipeline'):
            implicit_reqs['needs_error_handling'] = True
            implicit_reqs['needs_validation'] = True
        
        return implicit_reqs 

    def _get_required_tools(self, explicit_reqs: Dict[str, Any], implicit_reqs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get required tools based on requirements."""
        required_tools = []
        
        # Get tools from database
        cursor = self.db_conn.cursor()
        
        try:
            # Get tools for pipeline creation
            if explicit_reqs.get('needs_pipeline'):
                pipeline_types = explicit_reqs.get('pipeline_type', [])
                for pipeline_type in pipeline_types:
                    if 'databricks' in pipeline_type.lower():
                        cursor.execute("""
                            SELECT id, tool_name, tool_type, description
                            FROM tools
                            WHERE tool_name LIKE '%DBX%'
                            OR tool_name LIKE '%Databricks%'
                            LIMIT 1
                        """)
                        row = cursor.fetchone()
                        if row:
                            required_tools.append({
                                'id': row[0],
                                'tool_name': row[1],
                                'tool_type': row[2],
                                'description': row[3],
                                'match_reason': 'explicit_match'
                            })
                    
                    if 'nifi' in pipeline_type.lower():
                        cursor.execute("""
                            SELECT id, tool_name, tool_type, description
                            FROM tools
                            WHERE tool_name LIKE '%Nifi%'
                            OR tool_name LIKE '%NiFi%'
                            LIMIT 1
                        """)
                        row = cursor.fetchone()
                        if row:
                            required_tools.append({
                                'id': row[0],
                                'tool_name': row[1],
                                'tool_type': row[2],
                                'description': row[3],
                                'match_reason': 'explicit_match'
                            })
            
            # Get tools for data access
            if explicit_reqs.get('needs_data_access') or implicit_reqs.get('database_tools'):
                cursor.execute("""
                    SELECT id, tool_name, tool_type, description
                    FROM tools
                    WHERE tool_type = 'Database'
                    OR tool_name LIKE '%RDS%'
                    LIMIT 1
                """)
                row = cursor.fetchone()
                if row:
                    required_tools.append({
                        'id': row[0],
                        'tool_name': row[1],
                        'tool_type': row[2],
                        'description': row[3],
                        'match_reason': 'implicit_match'
                    })
            
            # Get tools for API access
            if explicit_reqs.get('needs_api'):
                cursor.execute("""
                    SELECT id, tool_name, tool_type, description
                    FROM tools
                    WHERE tool_type = 'APIService'
                    LIMIT 2
                """)
                for row in cursor.fetchall():
                    required_tools.append({
                        'id': row[0],
                        'tool_name': row[1],
                        'tool_type': row[2],
                        'description': row[3],
                        'match_reason': 'explicit_match'
                    })
            
            return required_tools
            
        finally:
            cursor.close() 