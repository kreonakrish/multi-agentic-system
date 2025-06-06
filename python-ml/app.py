from flask import Flask, request, jsonify
from abc import ABC, abstractmethod
import mysql.connector
from mysql.connector import pooling
import os
from datetime import datetime, timedelta
import openai  # Changed from 'from openai import OpenAI'
from typing import Dict, Any, List, Optional
import json
from enum import Enum
from collections import defaultdict
import logging
import logging.handlers
from functools import wraps
import traceback
import uuid
import sys
from dotenv import load_dotenv
import decimal
import httpx
import requests
import pandas as pd
from io import StringIO
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.utils.team_utils import (
    store_team_task,
    create_workflow_record,
    get_team_agents_ordered,
    group_agents_by_priority,
    create_workflow_steps,
    execute_priority_group,
    update_workflow_steps_status,
    update_workflow_status,
    aggregate_team_responses
)
from app.core.tools import Tool, GitHubTool, DatabaseTool, APITool, WebServiceTool, create_tool

# Configure logging first
from app.config.logging_config import configure_logging
configure_logging()

# Get the logger for this module
logger = logging.getLogger('multi_agent_system')

# Load environment variables
load_dotenv()

# Initialize OpenAI client
try:
    if os.getenv('OPENAI_API_KEY'):
        logger.info('OPENAI_API_KEY found in environment')
        openai.api_key = os.getenv('OPENAI_API_KEY')
    else:
        logger.warning('OPENAI_API_KEY not found in environment, using mock API key for testing')
        openai.api_key = 'sk-test-key'
except Exception as e:
    logger.error(f'Error initializing OpenAI client: {str(e)}')
    raise

def get_openai_client():
    """Get or initialize OpenAI client with proper error handling"""
    if not openai.api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        openai.api_key = api_key
    return openai

app = Flask(__name__)

def log_execution(f):
    """Decorator to add logging to API endpoints"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        correlation_id = str(uuid.uuid4())
        logger.info(
            f"Starting execution of {f.__name__}",
            extra={
                'correlation_id': correlation_id,
                'endpoint': f.__name__,
                'func_args': args,
                'func_kwargs': kwargs
            }
        )
        
        try:
            result = f(*args, **kwargs)
            logger.info(
                f"Completed execution of {f.__name__}",
                extra={
                    'correlation_id': correlation_id,
                    'endpoint': f.__name__,
                    'status': 'success'
                }
            )
            return result
        except Exception as e:
            logger.error(
                f"Error in {f.__name__}: {str(e)}",
                extra={
                    'correlation_id': correlation_id,
                    'endpoint': f.__name__,
                    'error_msg': str(e),
                    'traceback': traceback.format_exc()
                }
            )
            raise
    return wrapper

# Remove the local database configuration and pool creation
# Instead import from the centralized config
from app.config.database import get_db_connection, safe_close_connection, DB_CONFIG

def get_db_connection():
    """Get a connection from the pool with proper error handling and monitoring"""
    from app.config.database import get_db_connection as get_conn
    return get_conn()

class Tool(ABC):
    def __init__(self, tool_id, tool_name, hostname, username, password, auth_method, description):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.hostname = hostname
        self.username = username
        self.password = password
        self.auth_method = auth_method
        self.description = description

    def connect(self):
        """Base connect method that always returns True for now"""
        return True

    def get_default_response(self, command):
        """Get a structured default response for the tool"""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "tool_type": self.__class__.__name__,
            "hostname": self.hostname,
            "auth_method": self.auth_method,
            "command": command,
            "status": "success",
            "message": f"Agent has successfully used the {self.tool_name} ({self.__class__.__name__})"
        }

    def execute(self, command):
        """Base execute method that returns a default response"""
        return self.get_default_response(command)

class DatabaseTool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "database_specific": {
                "query_type": "simulated",
                "affected_rows": 0,
                "execution_time": "0.00s"
            }
        })
        return response

class APITool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "api_specific": {
                "endpoint": f"{self.hostname}/api/v1/simulate",
                "method": "GET",
                "response_time": "0.00s"
            }
        })
        return response

class WebServiceTool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "service_specific": {
                "service_endpoint": f"{self.hostname}/service/simulate",
                "service_type": "REST",
                "response_time": "0.00s"
            }
        })
        return response

class PythonTool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "python_specific": {
                "execution_time": "0.00s"
            }
        })
        return response

class ReactTool(Tool):
    def execute(self, command):
        response = self.get_default_response(command)
        response.update({
            "react_specific": {
                "execution_time": "0.00s"
            }
        })
        return response

class GitHubTool(Tool):
    def __init__(self, tool_id: int, tool_name: str, hostname: str, username: str, password: str, auth_method: str, description: str):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.logger = logging.getLogger(__name__)
        self.max_rows = 100  # Maximum number of rows to return

    def execute(self, command: str) -> Dict[str, Any]:
        """Execute the GitHub tool command."""
        try:
            self.logger.info(f"Executing GitHub tool with command: {command}")
            
            # First try to extract dataset name from the command
            dataset_name = self._extract_dataset_name_from_text(command)
            if not dataset_name:
                self.logger.warning("No dataset name found in command")
                return {
                    'status': 'error',
                    'message': 'No dataset name could be extracted from the command'
                }
            
            # Look up dataset in FiveThirtyEight index
            dataset_info = self._find_dataset_by_name(dataset_name)
            if not dataset_info:
                self.logger.warning(f"Dataset not found: {dataset_name}")
                return {
                    'status': 'error',
                    'message': f'Dataset not found: {dataset_name}'
                }
            
            # Construct URL for the dataset
            url = self._construct_dataset_url(dataset_info)
            if not url:
                self.logger.warning(f"Could not construct URL for dataset: {dataset_name}")
                return {
                    'status': 'error',
                    'message': f'Could not construct URL for dataset: {dataset_name}'
                }
            
            # Download and process the data
            try:
                response = requests.get(url)
                response.raise_for_status()
                
                # Parse CSV data
                import pandas as pd
                from io import StringIO
                import json
                
                df = pd.read_csv(StringIO(response.text))
                
                # Convert DataFrame to list of dictionaries
                data = df.to_dict('records')
                
                # Limit the number of rows if specified
                if self.max_rows and len(data) > self.max_rows:
                    data = data[:self.max_rows]
                
                self.logger.info(f"Successfully fetched dataset: {dataset_name}")

                # Create a user-friendly summary of the data
                summary = f"\nI've found and retrieved the {dataset_name} dataset from FiveThirtyEight. Here's what I found:\n\n"
                summary += f"Dataset: {dataset_info['name']}\n"
                summary += f"Source: {dataset_info['url']}\n"
                summary += f"Related Article: {dataset_info['article_url']}\n\n"
                
                if dataset_name == 'nfl-favorite-team':
                    summary += "This dataset contains NFL team picking categories with various metrics for each team. "
                    summary += "The data includes scores (0-100) for different categories like:\n"
                    summary += "- BMK (Bandwagon Metric)\n"
                    summary += "- UNI (Uniform/Jersey Appeal)\n"
                    summary += "- CCH (Coach Likability)\n"
                    summary += "- STX (Team Success and History)\n"
                    summary += "And many more factors that influence team preference.\n\n"
                
                summary += f"I've retrieved data for {len(data)} teams. Here are the first few entries:\n\n"
                
                # Add first 3 teams as examples
                for i, team in enumerate(data[:3]):
                    summary += f"{i+1}. {team['TEAM']}:\n"
                    summary += f"   - Success/History Score: {team['STX']}\n"
                    summary += f"   - Fan Loyalty Score: {team['FRL']}\n"
                    summary += f"   - Overall Performance: {team['PLA']}\n"
                    summary += "   ...\n"
                
                summary += "\nHere's the complete dataset in JSON format:\n\n```json\n"
                summary += json.dumps(data, indent=2)
                summary += "\n```\n\nWould you like to see more specific details about any particular team or category?"
                
                return {
                    'status': 'success',
                    'message': summary,
                    'github_data': {
                        'url': url,
                        'data': data,
                        'dataset_name': dataset_name,
                        'dataset_info': dataset_info
                    }
                }
                
            except Exception as e:
                self.logger.error(f"Failed to download dataset: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'Failed to download dataset: {str(e)}'
                }
            
        except Exception as e:
            self.logger.error(f"Error executing GitHub tool: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error executing GitHub tool: {str(e)}'
            }

    def _load_fivethirtyeight_index(self) -> List[Dict[str, str]]:
        """Load the FiveThirtyEight dataset index file."""
        try:
            index_url = "https://raw.githubusercontent.com/fivethirtyeight/data/master/index.csv"
            response = requests.get(index_url)
            response.raise_for_status()
            
            # Parse CSV data
            import pandas as pd
            from io import StringIO
            
            df = pd.read_csv(StringIO(response.text))
            self.logger.info(f"Successfully loaded index with {len(df)} datasets")
            
            # Convert to list of dictionaries
            return df.to_dict('records')
        except Exception as e:
            self.logger.error(f"Error loading FiveThirtyEight index: {str(e)}")
            return []

    def _find_dataset_by_name(self, dataset_name: str) -> Optional[Dict[str, str]]:
        """Find a dataset in the FiveThirtyEight index by name."""
        try:
            self.logger.info(f"Fetching FiveThirtyEight data index...")
            index = self._load_fivethirtyeight_index()
            
            # Clean up the dataset name
            clean_name = dataset_name.lower().strip()
            
            # First try exact match
            for dataset in index:
                if dataset['subfolder_name'].lower() == clean_name:
                    return {
                        'name': dataset['subfolder_name'],
                        'path': dataset['subfolder_name'],
                        'url': dataset['dataset_url'],
                        'article_url': dataset['article_url']
                    }
            
            # Then try partial match
            matches = [
                dataset for dataset in index 
                if clean_name in dataset['subfolder_name'].lower()
            ]
            
            if matches:
                if len(matches) > 1:
                    self.logger.info(f"Found multiple matches for {clean_name}, using first match")
                dataset = matches[0]
                return {
                    'name': dataset['subfolder_name'],
                    'path': dataset['subfolder_name'],
                    'url': dataset['dataset_url'],
                    'article_url': dataset['article_url']
                }
            
            self.logger.warning(f"No dataset found matching name: {clean_name}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error finding dataset: {str(e)}")
            return None

    def _construct_dataset_url(self, dataset_info: Dict[str, str]) -> Optional[str]:
        """Construct the raw GitHub URL for a dataset."""
        try:
            # For NFL favorite team dataset, we know the exact URL
            if dataset_info['name'] == 'nfl-favorite-team':
                url = "https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv"
                self.logger.info(f"Using known URL for NFL dataset: {url}")
                return url

            # Base URL for raw GitHub content
            base_url = "https://raw.githubusercontent.com/fivethirtyeight/data"
            
            # Get the dataset path
            dataset_path = dataset_info.get('path', '')
            if not dataset_path:
                self.logger.warning("Dataset path is empty")
                return None
            
            # Try different branch paths
            branch_paths = [
                "refs/heads/master",
                "master"
            ]
            
            # Try different file names
            file_names = [
                f"{dataset_path.split('/')[-1]}.csv",  # Dataset folder name
                "data.csv",
                "dataset.csv",
                "raw.csv"
            ]
            
            # Try each combination of branch path and file name
            for branch in branch_paths:
                for file_name in file_names:
                    url = f"{base_url}/{branch}/{dataset_path}/{file_name}"
                    
                    # Check if file exists
                    try:
                        response = requests.head(url)
                        if response.status_code == 200:
                            self.logger.info(f"Found dataset CSV URL: {url}")
                            return url
                    except:
                        continue
            
            # If no CSV found, try scraping the GitHub web page
            web_url = dataset_info.get('url', '')
            if web_url:
                try:
                    response = requests.get(web_url)
                    response.raise_for_status()
                    
                    # Look for CSV files in the HTML
                    import re
                    csv_files = re.findall(r'href="[^"]+\.csv"', response.text)
                    if csv_files:
                        # Extract the first CSV file name
                        csv_file = csv_files[0].split('"')[1].split('/')[-1]
                        url = f"{base_url}/master/{dataset_path}/{csv_file}"
                        self.logger.info(f"Found CSV file through web scraping: {url}")
                        return url
                except:
                    pass
            
            self.logger.warning(f"No CSV file found for dataset: {dataset_path}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error constructing dataset URL: {str(e)}")
            return None

    def _extract_dataset_name_from_text(self, text: str) -> Optional[str]:
        """Extract dataset name from natural language text using NLP techniques."""
        import re
        import nltk
        from nltk.tokenize import word_tokenize
        from nltk.tag import pos_tag
        
        try:
            # First try known dataset mappings
            known_mappings = {
                'nfl': 'nfl-favorite-team',
                'football': 'nfl-favorite-team',
                'favorite team': 'nfl-favorite-team',
                'team preference': 'nfl-favorite-team',
                'nfl favorite': 'nfl-favorite-team',
                'nfl favorite team': 'nfl-favorite-team',
                # Add more mappings as needed
            }
            
            # Try exact matches first
            text_lower = text.lower()
            for key, value in known_mappings.items():
                if key in text_lower:
                    self.logger.info(f"Found dataset name through known mappings: {value}")
                    return value
            
            # Download required NLTK data (only first time)
            try:
                nltk.download('punkt', quiet=True)
                nltk.download('averaged_perceptron_tagger', quiet=True)
            except Exception as e:
                self.logger.warning(f"Error downloading NLTK data: {str(e)}")
            
            # Try direct pattern matching
            patterns = [
                r'(?:get|fetch|download|retrieve|find|access)\s+(?:the\s+)?([a-zA-Z0-9-]+(?:-[a-zA-Z0-9-]+)*)\s+(?:dataset|data)',
                r'([a-zA-Z0-9-]+(?:-[a-zA-Z0-9-]+)*)\s+(?:dataset|data|prices)',
                r'data\s+(?:about|for|on)\s+([a-zA-Z0-9-]+(?:-[a-zA-Z0-9-]+)*)',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                if matches:
                    dataset_name = matches[0]
                    if isinstance(dataset_name, tuple):
                        dataset_name = dataset_name[0]
                    # Check if the extracted name maps to a known dataset
                    for key, value in known_mappings.items():
                        if key in dataset_name:
                            self.logger.info(f"Found dataset name through pattern matching and mapping: {value}")
                            return value
                    self.logger.info(f"Found dataset name through pattern matching: {dataset_name}")
                    return dataset_name
            
            # If no direct matches, try NLP-based extraction
            # Tokenize and tag parts of speech
            tokens = word_tokenize(text)
            tagged = pos_tag(tokens)
            
            # Look for noun phrases that might be dataset names
            dataset_indicators = {'dataset', 'data', 'information', 'stats', 'statistics', 'records', 'database'}
            potential_datasets = []
            
            for i, (word, tag) in enumerate(tagged):
                # If we find a dataset indicator word
                if word.lower() in dataset_indicators:
                    # Look at previous words for potential dataset name
                    start_idx = max(0, i-3)
                    phrase = []
                    for j in range(start_idx, i):
                        if tagged[j][1].startswith(('NN', 'JJ')):  # Nouns and adjectives
                            phrase.append(tagged[j][0])
                    if phrase:
                        potential_name = '-'.join(phrase).lower()
                        # Check if the extracted name maps to a known dataset
                        for key, value in known_mappings.items():
                            if key in potential_name:
                                self.logger.info(f"Found dataset name through NLP and mapping: {value}")
                                return value
                        potential_datasets.append(potential_name)
            
            if potential_datasets:
                # Try each potential dataset name
                for dataset_name in potential_datasets:
                    # Clean up the dataset name
                    dataset_name = re.sub(r'[^a-zA-Z0-9-]', '-', dataset_name)
                    dataset_name = re.sub(r'-+', '-', dataset_name)
                    dataset_name = dataset_name.strip('-')
                    
                    self.logger.info(f"Found potential dataset name through NLP: {dataset_name}")
                    
                    # Verify if this dataset exists
                    dataset_info = self._find_dataset_by_name(dataset_name)
                    if dataset_info:
                        self.logger.info(f"Verified dataset exists: {dataset_name}")
                        return dataset_name
            
            # If still no match, try extracting just the NFL part
            if 'nfl' in text_lower:
                self.logger.info("Found NFL reference, using nfl-favorite-team dataset")
                return 'nfl-favorite-team'
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting dataset name: {str(e)}")
            return None

    def validate_response(self, validation_json: str) -> Dict[str, Any]:
        """Validate and process the response from LLM."""
        try:
            # Check if LLM response has a GitHub CSV raw URL
            pattern = r'https://raw\.githubusercontent\.com/[^\s\'"]+'
            match = re.search(pattern, validation_json)
            if match:
                github_url = match.group(0)
                self.logger.info(f"Found GitHub URL: {github_url}")
                
                # Try to download and process the data
                try:
                    response = requests.get(github_url)
                    response.raise_for_status()
                    
                    # Parse CSV data
                    import pandas as pd
                    from io import StringIO
                    
                    df = pd.read_csv(StringIO(response.text))
                    
                    # Convert DataFrame to list of dictionaries
                    data = df.to_dict('records')
                    
                    # Limit the number of rows if specified
                    if self.max_rows and len(data) > self.max_rows:
                        data = data[:self.max_rows]
                    
                    return {
                        'status': 'success',
                        'github_data': {
                            'url': github_url,
                            'data': data
                        }
                    }
                    
                except Exception as e:
                    self.logger.error(f"Failed to download GitHub data: {str(e)}")
                    return {
                        'status': 'error',
                        'message': f'Failed to download GitHub data: {str(e)}'
                    }
            
            # If no direct URL found, try to extract dataset name
            dataset_name = self._extract_dataset_name_from_text(validation_json)
            if dataset_name:
                self.logger.info(f"Found dataset name: {dataset_name}")
                # Look up dataset in index
                dataset_info = self._find_dataset_by_name(dataset_name)
                if dataset_info:
                    url = self._construct_dataset_url(dataset_info)
                    if url:
                        # Download and process the data
                        try:
                            response = requests.get(url)
                            response.raise_for_status()
                            
                            # Parse CSV data
                            import pandas as pd
                            from io import StringIO
                            
                            df = pd.read_csv(StringIO(response.text))
                            
                            # Convert DataFrame to list of dictionaries
                            data = df.to_dict('records')
                            
                            # Limit the number of rows if specified
                            if self.max_rows and len(data) > self.max_rows:
                                data = data[:self.max_rows]
                            
                            return {
                                'status': 'success',
                                'github_data': {
                                    'url': url,
                                    'data': data
                                }
                            }
                            
                        except Exception as e:
                            self.logger.error(f"Failed to download GitHub data: {str(e)}")
                            return {
                                'status': 'error',
                                'message': f'Failed to download GitHub data: {str(e)}'
                            }
            
            return {
                'status': 'error',
                'message': 'No GitHub URL or dataset found in response'
            }
            
        except Exception as e:
            self.logger.error(f"Error validating response: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error validating response: {str(e)}'
            }

class InteractionType(Enum):
    DIRECT = "direct"
    WORKFLOW = "workflow"
    BROADCAST = "broadcast"
    CHAIN = "chain"

class InteractionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentInteraction:
    def __init__(self, 
                 interaction_id: int,
                 source_agent_id: int,
                 target_agent_id: int,
                 interaction_type: str,
                 message: str,
                 status: str = InteractionStatus.PENDING.value):
        self.interaction_id = interaction_id
        self.source_agent_id = source_agent_id
        self.target_agent_id = target_agent_id
        self.interaction_type = interaction_type
        self.message = message
        self.status = status
        self.response = None
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "interaction_id": self.interaction_id,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "interaction_type": self.interaction_type,
            "message": self.message,
            "status": self.status,
            "response": self.response,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class TeamPermission:
    def __init__(self, team_id: int, tool_id: int, permission_level: str):
        self.team_id = team_id
        self.tool_id = tool_id
        self.permission_level = permission_level  # read, write, admin

class TeamConfig:
    def __init__(self, team_id: int, name: str, config_data: Dict[str, Any]):
        self.team_id = team_id
        self.name = name
        self.config_data = config_data
        self.permissions = []
        self.metrics = TeamMetrics(team_id)

    def add_permission(self, tool_id: int, permission_level: str):
        self.permissions.append(TeamPermission(self.team_id, tool_id, permission_level))

    def has_permission(self, tool_id: int, required_level: str) -> bool:
        for perm in self.permissions:
            if perm.tool_id == tool_id:
                if required_level == 'read' and perm.permission_level in ['read', 'write', 'admin']:
                    return True
                if required_level == 'write' and perm.permission_level in ['write', 'admin']:
                    return True
                if required_level == 'admin' and perm.permission_level == 'admin':
                    return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "config": self.config_data,
            "permissions": [
                {
                    "tool_id": p.tool_id,
                    "level": p.permission_level
                } for p in self.permissions
            ]
        }

class TeamMetrics:
    def __init__(self, team_id: int):
        self.team_id = team_id
        self.interaction_counts = defaultdict(int)
        self.tool_usage = defaultdict(int)
        self.success_rate = defaultdict(float)
        self.response_times = defaultdict(list)
        self.last_updated = datetime.now()

    def update_metrics(self, metric_type: str, value: Any):
        if metric_type == "interaction":
            self.interaction_counts[value] += 1
        elif metric_type == "tool_usage":
            self.tool_usage[value] += 1
        elif metric_type == "success_rate":
            self.success_rate[value[0]] = value[1]
        elif metric_type == "response_time":
            self.response_times[value[0]].append(value[1])
        
        self.last_updated = datetime.now()

    def get_metrics(self, time_range: str = "24h") -> Dict[str, Any]:
        cutoff = datetime.now()
        if time_range == "24h":
            cutoff = cutoff - timedelta(hours=24)
        elif time_range == "7d":
            cutoff = cutoff - timedelta(days=7)
        elif time_range == "30d":
            cutoff = cutoff - timedelta(days=30)

        return {
            "team_id": self.team_id,
            "interaction_counts": dict(self.interaction_counts),
            "tool_usage": dict(self.tool_usage),
            "success_rate": dict(self.success_rate),
            "average_response_times": {
                tool_id: sum(times)/len(times) if times else 0 
                for tool_id, times in self.response_times.items()
            },
            "last_updated": self.last_updated.isoformat()
        }

class Agent:
    def __init__(self, agent_id: int, name: str, memory_type: str, foundation_model: str, team_id: Optional[int] = None, use_prod: bool = False):
        self.agent_id = agent_id
        self.name = name
        self.memory_type = memory_type
        self.foundation_model = foundation_model
        self.use_prod = use_prod
        self.team_id = team_id
        self.team_config = None
        self.tools = []
        self.memories = []
        self.pending_interactions = []
        self.interaction_history = []
        self.correlation_id = None
        self.logger = logging.getLogger(f'multi_agent_system.agent.{agent_id}')
        
        # Log agent initialization
        self.log('info', 'Agent initialized', 
                memory_type=memory_type,
                foundation_model=foundation_model,
                team_id=team_id)

    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for tracking agent actions"""
        self.correlation_id = correlation_id
        self.log('info', 'Correlation ID set', correlation_id=correlation_id)

    def log(self, level: str, message: str, **kwargs):
        """Structured logging for agent actions"""
        # Extract exc_info from kwargs if present
        exc_info = kwargs.pop('exc_info', None)
        
        # Add default context
        extra = {
            'correlation_id': self.correlation_id or 'NO_CORRELATION_ID',
            'agent_id': self.agent_id,
            'agent_name': self.name,
            'team_id': self.team_id,
            'memory_type': self.memory_type,
            'foundation_model': self.foundation_model
        }
        
        # Add additional context from kwargs
        extra.update(kwargs)
        
        # Call logger with proper exc_info handling
        if exc_info:
            getattr(self.logger, level)(message, extra=extra, exc_info=exc_info)
        else:
            getattr(self.logger, level)(message, extra=extra)

    def get_llm_response(self, command: str, context: str = "") -> Dict[str, Any]:
        """Get response from LLM with proper formatting and processing"""
        try:
            # Format messages for LLM
            messages = self.format_messages_for_llm(command, context)
            
            # Process with LLM
            llm_response = self.process_with_llm(messages)
            
            if llm_response["status"] != "success":
                self.log('error', "LLM processing failed", 
                        error=llm_response.get("message", "Unknown error"))
                return llm_response
            
            return {
                "status": "success",
                "response": llm_response["response"],
                "model_used": llm_response["model_used"],
                "conversation_id": llm_response.get("conversation_id")
            }
            
        except Exception as e:
            self.log('error', f"Error in get_llm_response: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Failed to get LLM response: {str(e)}"
            }

    def load_team_config(self, cursor) -> bool:
        """Load team configuration and permissions"""
        if not self.team_id:
            return False

        # Get team details
        cursor.execute("SELECT * FROM teams WHERE id = %s", (self.team_id,))
        team_data = cursor.fetchone()
        if not team_data:
            return False

        # Get team configuration
        cursor.execute("SELECT * FROM team_configurations WHERE team_id = %s", (self.team_id,))
        config_data = cursor.fetchone() or {}

        # Create team config
        self.team_config = TeamConfig(self.team_id, team_data['name'], config_data)

        # Load team permissions
        cursor.execute("""
            SELECT tool_id, permission_level 
            FROM team_permissions 
            WHERE team_id = %s
        """, (self.team_id,))
        
        permissions = cursor.fetchall()
        for perm in permissions:
            self.team_config.add_permission(perm['tool_id'], perm['permission_level'])

        return True

    def check_tool_permission(self, tool_id: int, required_level: str) -> bool:
        """Check if the agent's team has required permission for the tool"""
        if not self.team_config:
            return False
        return self.team_config.has_permission(tool_id, required_level)

    def update_team_metrics(self, metric_type: str, value: Any):
        """Update team metrics"""
        if self.team_config and self.team_config.metrics:
            self.team_config.metrics.update_metrics(metric_type, value)

    def execute_with_tool(self, tool_id: int, command: str) -> Dict[str, Any]:
        """Execute command with permission check, metrics tracking, and logging"""
        self.log('info', 'Starting tool execution', tool_id=tool_id, command=command)
        
        # Check permissions
        if not self.check_tool_permission(tool_id, 'write'):
            self.log('warning', 'Permission denied for tool execution', 
                    tool_id=tool_id, required_permission='write')
            return {"status": "error", "message": "Insufficient permissions for this tool"}

        start_time = datetime.now()
        try:
            result = super().execute_with_tool(tool_id, command)
            execution_time = (datetime.now() - start_time).total_seconds()

            # Log execution result
            self.log('info', 'Tool execution completed',
                    tool_id=tool_id,
                    execution_time=execution_time,
                    status=result["status"])

            # Update metrics
            if self.team_config:
                self.update_team_metrics("tool_usage", tool_id)
                self.update_team_metrics("response_time", (tool_id, execution_time))
                self.update_team_metrics("success_rate", 
                    (tool_id, 1.0 if result["status"] == "success" else 0.0))

            return result
        except Exception as e:
            self.log('error', f'Tool execution failed: {str(e)}',
                    tool_id=tool_id,
                    error=str(e),
                    traceback=traceback.format_exc())
            raise

    def add_tool(self, tool):
        self.tools.append(tool)

    def remove_tool(self, tool_id):
        self.tools = [t for t in self.tools if t.tool_id != tool_id]

    def load_memories(self, cursor):
        """Load agent's memories from database"""
        cursor.execute("""
            SELECT * FROM agent_memory 
            WHERE agent_id = %s 
            ORDER BY updated_at DESC
        """, (self.agent_id,))
        self.memories = cursor.fetchall()
        return self.memories

    def get_context_from_memories(self):
        """Get relevant context from agent's memories"""
        if not self.memories:
            return ""
        
        # Get the most recently updated memory
        latest_memory = self.memories[0]
        context = []
        
        if latest_memory['start_prompt']:
            context.append(f"Start Prompt: {latest_memory['start_prompt']}")
        if latest_memory['context']:
            context.append(f"Context: {latest_memory['context']}")
        if latest_memory['end_prompt']:
            context.append(f"End Prompt: {latest_memory['end_prompt']}")
        
        return "\n".join(context)

    def process_with_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        try:
            # Get OpenAI client with error handling
            try:
                openai_client = get_openai_client()
            except ValueError as e:
                self.log('error', f"OpenAI client initialization failed: {str(e)}")
                return {"status": "error", "message": str(e)}

            # Log the request to OpenAI
            request_params = {
                'model': 'gpt-4',
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 1000
            }
            self.log('info', 'Sending request to OpenAI API...', 
                    openai_request=request_params)
            
            # Use OpenAI's chat completion
            response = openai_client.ChatCompletion.create(**request_params)
            
            # Log the response from OpenAI
            response_data = {
                'content': response.choices[0].message['content'],
                'finish_reason': response.choices[0].finish_reason,
                'usage': response.usage._previous
            }
            self.log('info', 'Received response from OpenAI API',
                    openai_response=response_data)
            
            self.log('debug', f"Model response: {response.choices[0].message['content']}")
            
            # Store OpenAI's response in database
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                # Store OpenAI's response
                insert_query = """
                    INSERT INTO messages 
                    (sender_id, receiver_id, content, interaction_type, conversation_id, team_id, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    None,  # sender_id (OpenAI sending to agent)
                    self.agent_id,  # receiver_id
                    response.choices[0].message['content'],
                    'foundation_model',
                    self.correlation_id,
                    self.team_id,
                    'processed'
                ))
                
                conn.commit()
            except Exception as db_error:
                self.log('error', f"Database error storing OpenAI response: {str(db_error)}")
                if conn:
                    conn.rollback()
            finally:
                safe_close_connection(conn, cursor)
            
            return {
                'status': 'success',
                'response': response.choices[0].message['content'],
                'usage': response.usage._previous
            }
            
        except Exception as e:
            self.log('error', f"Error in process_with_llm: {str(e)}", exc_info=True)
            raise

    def format_messages_for_llm(self, command: str, context: str = "") -> List[Dict[str, str]]:
        """Format messages for LLM with proper context"""
        messages = []
        
        # Add system message with agent context
        system_msg = f"""You are {self.name}, an AI agent with access to GitHub tools and datasets. Your role is to help users find and analyze data from GitHub repositories, particularly from FiveThirtyEight's data collection.

IMPORTANT: When users mention any dataset (like "nfl favorite team", "nfl data", etc.), you MUST:
1. ALWAYS use the GitHub Tool to fetch the actual dataset
2. DO NOT treat it as a conversational question
3. DO NOT ask for clarification unless the dataset name is completely unclear
4. DO NOT say you're an AI or talk about preferences
5. Instead, immediately use the GitHub Tool to get the data

For example:
- If user asks "nfl favorite team" -> Use GitHub Tool to get the NFL favorite team dataset
- If user asks "show me nfl data" -> Use GitHub Tool to get the NFL dataset
- If user asks "what's your favorite nfl team" -> Still use GitHub Tool as this implies they want the NFL team dataset

Context: {context}"""
        messages.append({"role": "system", "content": system_msg})
        
        # Add available tools information with specific instructions
        if self.tools:
            tools_msg = "Available tools:\n"
            for tool in self.tools:
                if isinstance(tool, GitHubTool):
                    tools_msg += f"""- {tool.tool_name}: This tool allows you to:
  * Access FiveThirtyEight's datasets directly
  * Extract and analyze data from GitHub repositories
  * Process and present data in a user-friendly format
  * Provide insights and summaries from the data
"""
                else:
                    tools_msg += f"- {tool.tool_name}: {tool.description}\n"
            messages.append({"role": "system", "content": tools_msg})
        
        # Add user command
        messages.append({"role": "user", "content": command})
        
        self.log('debug', 'Formatted messages for LLM',
                params={'messages': messages})
        
        return messages

    def download_github_data(self, url: str) -> Dict[str, Any]:
        """
        Download data from GitHub raw URL and convert to JSON
        """
        try:
            # Download the CSV data
            response = requests.get(url)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Read CSV into pandas DataFrame
            df = pd.read_csv(StringIO(response.text))
            
            # Convert to JSON format (first 100 rows to avoid huge responses)
            json_data = df.head(100).to_json(orient='records')
            
            return {
                "status": "success",
                "data": json.loads(json_data),
                "total_rows": len(df),
                "returned_rows": len(json_data),
                "columns": list(df.columns),
                "source_url": url
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to download data: {str(e)}",
                "source_url": url
            }

    def validate_response_with_llm(self, response: str, end_prompt: str) -> Dict[str, Any]:
        """
        Validate if the response satisfies the end prompt using the foundation model
        """
        logger.info(f"[validate_response_with_llm] Starting validation for agent {self.agent_id}")
        logger.info(f"[validate_response_with_llm] End prompt: {end_prompt}")
        logger.debug(f"[validate_response_with_llm] Response to validate: {response}")
        
        validation_messages = [
            {
                "role": "system",
                "content": "You are a validation agent. Your task is to verify if the given response satisfies the end prompt requirements. Return a JSON with format: {\"valid\": boolean, \"reason\": string, \"github_url\": string if present}"
            },
            {
                "role": "user",
                "content": f"End Prompt Requirements:\n{end_prompt}\n\nResponse to Validate:\n{response}\n\nDoes this response satisfy the end prompt requirements? If the response contains a GitHub URL, include it in the github_url field. Provide your assessment in the required JSON format."
            }
        ]

        try:
            logger.info("[validate_response_with_llm] Sending validation request to OpenAI")
            logger.debug(f"[validate_response_with_llm] Validation messages: {json.dumps(validation_messages, indent=2)}")
            
            validation_response = get_openai_client().chat.completions.create(
                model="gpt-4",
                messages=validation_messages,
                temperature=0.3,  # Lower temperature for more consistent validation
                max_tokens=500
            )
            
            validation_result = validation_response.choices[0].message.content
            logger.info("[validate_response_with_llm] Received validation response from OpenAI")
            logger.debug(f"[validate_response_with_llm] Raw validation result: {validation_result}")
            
            try:
                validation_json = json.loads(validation_result)
                
                # Log validation outcome
                if validation_json.get("valid", False):
                    logger.info("[validate_response_with_llm] Validation successful")
                    logger.info(f"[validate_response_with_llm] Validation reason: {validation_json.get('reason')}")
                else:
                    logger.warning("[validate_response_with_llm] Validation failed")
                    logger.warning(f"[validate_response_with_llm] Failure reason: {validation_json.get('reason')}")
                    # Log the complete context when validation fails
                    logger.warning("=== Validation Failure Context ===")
                    logger.warning(f"Agent ID: {self.agent_id}")
                    logger.warning(f"End Prompt: {end_prompt}")
                    logger.warning(f"Response being validated: {response}")
                    logger.warning(f"Messages sent to OpenAI: {json.dumps(validation_messages, indent=2)}")
                    logger.warning(f"OpenAI response: {validation_result}")
                    logger.warning("===============================")
                
                # Check if LLM response has a GitHub CSV raw URL
                pattern = r'https://raw\.githubusercontent\.com/[^\s\'"]'
                match = re.search(pattern, validation_json)
                if match:
                    github_url = match.group(0)
                    logger.info(f"[validate_response_with_llm] Found GitHub URL: {github_url}")
                    github_agent_context = {
                        "team_id": 77,
                        "conversation_settings_id": 131,
                        "agent_id": 92
                    }

                    # Download data from GitHub
                    github_data = self.download_github_data(validation_json["github_url"])
                    
                    # Combine validation result with GitHub data
                    return {
                        "status": "success",
                        "valid": validation_json.get("valid", False),
                        "reason": validation_json.get("reason", "No reason provided"),
                        "github_data": github_data,
                        "agent_context": github_agent_context
                    }
                
                # Regular validation response without GitHub URL
                return {
                    "status": "success",
                    "valid": validation_json.get("valid", False),
                    "reason": validation_json.get("reason", "No reason provided")
                }
                
            except json.JSONDecodeError as json_error:
                logger.error(f"[validate_response_with_llm] Failed to parse validation response: {str(json_error)}")
                logger.error(f"[validate_response_with_llm] Raw response that failed parsing: {validation_result}")
                return {
                    "status": "error",
                    "message": "Failed to parse validation response",
                    "raw_response": validation_result
                }
                
        except Exception as e:
            logger.error(f"[validate_response_with_llm] Validation failed with error: {str(e)}", exc_info=True)
            return {"status": "error", "message": f"Validation failed: {str(e)}"}

    def execute_with_tools(self, command: str) -> Dict[str, Any]:
        """Execute command with all available tools"""
        try:
            self.log('info', '[execute_with_tools] Starting execution', 
                    params={'command': command})
            
            # Format messages for LLM
            messages = self.format_messages_for_llm(command)
            self.log('debug', 'Formatted messages for LLM',
                    params={'formatted_messages': messages})
            
            # Get response from LLM
            llm_response = self.process_with_llm(messages)
            if llm_response.get('status') == 'error':
                return llm_response
            
            # Execute tools based on LLM response
            tool_results = []
            combined_response = ""
            github_data = None
            
            for tool in self.tools:
                try:
                    self.log('debug', f'Executing tool {tool.tool_name}',
                            params={'tool_input': llm_response['response']})
                    result = tool.execute(llm_response['response'])
                    
                    # Add tool result
                    tool_results.append({
                        "tool_name": tool.tool_name,
                        "status": "success",
                        "result": result
                    })
                    
                    # Build combined response
                    if result.get('status') == 'success':
                        if result.get('message'):
                            # If tool returned a formatted message, use it
                            combined_response = result['message']
                        
                        # Store GitHub data if present
                        if result.get('github_data'):
                            github_data = result['github_data']
                    
                    self.log('debug', f'Tool {tool.tool_name} execution completed',
                            params={'tool_result': result})
                except Exception as tool_error:
                    self.log('error', f"Error executing tool {tool.tool_name}: {str(tool_error)}")
                    tool_results.append({
                        "tool_name": tool.tool_name,
                        "status": "error",
                        "error": str(tool_error)
                    })
            
            # If no tool-specific response was generated, use the LLM response
            if not combined_response:
                combined_response = llm_response['response']
            
            self.log('info', '[execute_with_tools] Successfully completed execution',
                    params={'tool_results': tool_results})
            
            response = {
                "status": "success",
                "message": combined_response,
                "llm_response": llm_response['response'],
                "tool_results": tool_results
            }
            
            # Include GitHub data if present
            if github_data:
                response["github_data"] = github_data
            
            return response
            
        except Exception as e:
            self.log('error', f"[execute_with_tools] Unhandled error: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "details": traceback.format_exc()
            }

    def execute_with_tool(self, tool_id: int, command: str) -> Dict[str, Any]:
        """Legacy method for single tool execution"""
        tool = next((t for t in self.tools if t.tool_id == tool_id), None)
        if not tool:
            return {"status": "error", "message": "Tool not found"}
        
        # Get context from memories
        context = self.get_context_from_memories()
        end_prompt = None
        if self.memories and self.memories[0].get('end_prompt'):
            end_prompt = self.memories[0]['end_prompt']
        
        if tool.connect():
            messages = self.format_messages_for_llm(command, context)
            llm_response = self.process_with_llm(messages)
            
            if llm_response["status"] != "success":
                return llm_response
            
            result = tool.execute(llm_response["response"])
            
            validation_result = None
            if end_prompt and result["status"] == "success":
                validation_result = self.validate_response_with_llm(
                    str(result),
                    end_prompt
                )
                
                if validation_result["status"] == "success" and not validation_result["valid"]:
                    result["validation_warning"] = validation_result["reason"]
            
            result.update({
                "context": context,
                "memory_type": self.memory_type,
                "llm_response": llm_response["response"],
                "model_used": llm_response["model_used"],
                "validation_result": validation_result
            })
            
            return result
        return {"status": "error", "message": "Failed to connect to tool"}

    def send_message(self, target_agent_id: int, message: str, interaction_type: str = InteractionType.DIRECT.value) -> Dict[str, Any]:
        """Send a message to another agent with logging"""
        self.log('info', 'Sending message to agent',
                target_agent_id=target_agent_id,
                interaction_type=interaction_type)
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            # Create new interaction
            cursor.execute("""
                INSERT INTO agent_interactions 
                (source_agent_id, target_agent_id, interaction_type, message, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (self.agent_id, target_agent_id, interaction_type, message, InteractionStatus.PENDING.value))
            
            interaction_id = cursor.lastrowid
            conn.commit()

            # Create interaction object
            interaction = AgentInteraction(
                interaction_id,
                self.agent_id,
                target_agent_id,
                interaction_type,
                message
            )

            # Process the message with LLM before sending
            messages = self.format_messages_for_llm(
                f"Process this message for agent {target_agent_id}: {message}",
                context=self.get_context_from_memories()
            )
            llm_response = self.process_with_llm(messages)

            if llm_response["status"] == "success":
                processed_message = llm_response["response"]
                
                # Update interaction with processed message
                cursor.execute("""
                    UPDATE agent_interactions 
                    SET processed_message = %s,
                        status = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (processed_message, InteractionStatus.IN_PROGRESS.value, interaction_id))
                conn.commit()

                interaction.message = processed_message
                interaction.status = InteractionStatus.IN_PROGRESS.value

            cursor.close()
            conn.close()

            self.log('info', 'Message sent successfully',
                    target_agent_id=target_agent_id,
                    interaction_id=interaction.interaction_id)
            
            return {
                "status": "success",
                "interaction": interaction.to_dict(),
                "llm_response": llm_response.get("response")
            }

        except Exception as e:
            self.log('error', f'Failed to send message: {str(e)}',
                    target_agent_id=target_agent_id,
                    error=str(e),
                    traceback=traceback.format_exc())
            raise

    def receive_message(self, interaction_id: int) -> Dict[str, Any]:
        """Process a received message"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get message details
            cursor.execute("""
                SELECT id, sender_id, receiver_id, content, processed_message,
                       interaction_type, status, created_at
                FROM messages 
                WHERE id = %s AND receiver_id = %s
            """, (interaction_id, self.agent_id))
            
            message = cursor.fetchone()
            if not message:
                return {
                    'status': 'error',
                    'message': 'Message not found'
                }
            
            # Convert datetime objects to strings for JSON serialization
            if message and message.get('created_at'):
                if isinstance(message['created_at'], datetime):
                    message['created_at'] = message['created_at'].isoformat()
                else:
                    message['created_at'] = str(message['created_at'])
            
            # Update message status
            cursor.execute("""
                UPDATE messages 
                SET status = 'processed',
                    processed_message = content
                WHERE id = %s
            """, (interaction_id,))
            
            conn.commit()
            
            return {
                'status': 'success',
                'message': message
            }
            
        except Exception as e:
            self.log('error', f"Error receiving message: {str(e)}")
            if conn:
                conn.rollback()
            return {
                'status': 'error',
                'message': str(e)
            }
        finally:
            safe_close_connection(conn, cursor)

    def start_workflow(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Start a multi-agent workflow"""
        try:
            workflow_type = workflow_data.get("type", "sequential")
            agents = workflow_data.get("agents", [])
            message = workflow_data.get("message", "")

            if not agents:
                return {"status": "error", "message": "No agents specified for workflow"}

            if workflow_type == "sequential":
                return self._start_sequential_workflow(agents, message)
            elif workflow_type == "broadcast":
                return self._start_broadcast_workflow(agents, message)
            else:
                return {"status": "error", "message": f"Unsupported workflow type: {workflow_type}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _start_sequential_workflow(self, agents: List[int], message: str) -> Dict[str, Any]:
        """Start a sequential workflow where agents process in sequence"""
        try:
            interactions = []
            current_message = message

            for i, target_agent_id in enumerate(agents):
                # Send message to next agent in sequence
                result = self.send_message(
                    target_agent_id,
                    current_message,
                    InteractionType.WORKFLOW.value
                )

                if result["status"] != "success":
                    return result

                interactions.append(result["interaction"])
                current_message = result["llm_response"]

            return {
                "status": "success",
                "workflow_type": "sequential",
                "interactions": interactions
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _start_broadcast_workflow(self, agents: List[int], message: str) -> Dict[str, Any]:
        """Start a broadcast workflow where message is sent to all agents simultaneously"""
        try:
            interactions = []

            for target_agent_id in agents:
                result = self.send_message(
                    target_agent_id,
                    message,
                    InteractionType.BROADCAST.value
                )

                if result["status"] == "success":
                    interactions.append(result["interaction"])

            return {
                "status": "success",
                "workflow_type": "broadcast",
                "interactions": interactions
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

class TeamTask:
    def __init__(self, task_id: str, description: str, requirements: Dict[str, Any]):
        self.task_id = task_id
        self.description = description
        self.requirements = requirements
        self.status = "pending"
        self.results = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "requirements": self.requirements,
            "status": self.status,
            "results": self.results,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class TeamMember:
    def __init__(self, agent_id: int, priority: int, accuracy_threshold: float, success_rate: float):
        self.agent_id = agent_id
        self.priority = priority
        self.accuracy_threshold = accuracy_threshold
        self.success_rate = success_rate
        self.current_task = None
        self.results = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "priority": self.priority,
            "accuracy_threshold": self.accuracy_threshold,
            "success_rate": self.success_rate,
            "current_task": self.current_task.to_dict() if self.current_task else None,
            "results": self.results
        }

class Team:
    def __init__(self, team_id: str, name: str, description: str):
        self.team_id = team_id
        self.name = name
        self.description = description
        self.members: List[TeamMember] = []
        self.tasks: List[TeamTask] = []
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def add_member(self, member: TeamMember):
        self.members.append(member)
        # Sort members by priority (highest first)
        self.members.sort(key=lambda x: x.priority, reverse=True)

    def assign_task(self, task: TeamTask):
        self.tasks.append(task)
        self.updated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "description": self.description,
            "members": [member.to_dict() for member in self.members],
            "tasks": [task.to_dict() for task in self.tasks],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

def execute_task_with_team(team: Team, task: TeamTask) -> Dict[str, Any]:
    """Execute a task using a team of agents with proper coordination"""
    try:
        logger.info(f"Starting team execution for task {task.task_id}")
        final_results = []
        
        # Track conversation context
        conversation_context = []
        
        # Get team agents from database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            # Convert team_id to int if it's numeric
            try:
                numeric_team_id = int(team.team_id)
            except (ValueError, TypeError):
                numeric_team_id = team.team_id
                
            logger.info(f"Fetching agents for team {numeric_team_id} (original team_id: {team.team_id})")
            
            # Fetch all agents for this team with their properties
            cursor.execute("""
                SELECT ta.agent_id, ta.accuracy, ta.success, ta.priority, a.name
                FROM team_agents ta
                JOIN agents a ON ta.agent_id = a.id
                WHERE ta.team_id = %s
                ORDER BY ta.priority DESC, ta.success DESC, ta.accuracy DESC
            """, (numeric_team_id,))
            
            team_agents = cursor.fetchall()
            logger.info(f"Found {len(team_agents)} agents for team {team.team_id}")
            
            if not team_agents:
                raise Exception(f"No agents found for team {team.team_id}")

            # Group agents by priority
            priority_groups = {}
            for agent_data in team_agents:
                priority = agent_data['priority']
                if priority not in priority_groups:
                    priority_groups[priority] = []
                priority_groups[priority].append(agent_data)

            # Sort priorities in descending order (highest priority first)
            sorted_priorities = sorted(priority_groups.keys(), reverse=True)
            logger.info(f"Executing agents in priority groups: {sorted_priorities}")

            # Execute agents priority by priority
            for priority in sorted_priorities:
                agents_in_group = priority_groups[priority]
                logger.info(f"Executing priority {priority} group with {len(agents_in_group)} agents")

                # Filter agents based on accuracy and success thresholds
                qualified_agents = [
                    agent for agent in agents_in_group
                    if (agent['accuracy'] or 0) >= task.requirements.get('min_accuracy', 0) and
                    (agent['success'] or 0) >= task.requirements.get('min_success_rate', 0)
                ]

                if not qualified_agents:
                    logger.warning(f"No qualified agents found in priority {priority} group")
                    continue

                # Initialize all agents in this priority group
                priority_group_results = []
                for agent_data in qualified_agents:
                    try:
                        # Initialize agent
                        agent = initialize_agent_from_db(agent_data['agent_id'])
                        if not agent:
                            logger.error(f"Could not initialize agent {agent_data['agent_id']}")
                            continue

                        logger.info(f"Executing with agent {agent_data['agent_id']} ({agent_data['name']}) - "
                                  f"Priority: {priority}, Accuracy: {agent_data['accuracy']}, "
                                  f"Success Rate: {agent_data['success']}")

                        # Set correlation ID for tracking
                        agent.set_correlation_id(task.task_id)

                        # Prepare message with context and requirements
                        message = {
                            "task_description": task.description,
                            "requirements": task.requirements,
                            "conversation_context": conversation_context,
                            "accuracy_threshold": agent_data['accuracy'] or 0.8,
                            "success_rate": agent_data['success'] or 0.9,
                            "priority": priority
                        }

                        # Execute with agent
                        result = agent.execute_with_tools(json.dumps(message))
                        
                        if result.get('status') == 'success':
                            # Format code blocks in response if present
                            response_text = result.get('llm_response', '')
                            if any(lang in response_text.lower() for lang in ['python', 'java', 'javascript', 'typescript', 'bash', 'sql']):
                                # Extract and format code blocks
                                formatted_response = []
                                lines = response_text.split('\n')
                                in_code_block = False
                                current_block = []
                                current_language = ''
                                
                                for line in lines:
                                    if line.startswith('```'):
                                        if in_code_block:
                                            # End code block
                                            formatted_response.append(f"```{current_language}\n{''.join(current_block)}\n```")
                                            current_block = []
                                            in_code_block = False
                                        else:
                                            # Start code block
                                            in_code_block = True
                                            current_language = line[3:].strip()
                                    elif in_code_block:
                                        current_block.append(line + '\n')
                                    else:
                                        formatted_response.append(line)
                                
                                response_text = '\n'.join(formatted_response)
                            
                            # Add to conversation context
                            conversation_context.append({
                                "agent_id": agent_data['agent_id'],
                                "agent_name": agent_data['name'],
                                "priority": priority,
                                "accuracy": agent_data['accuracy'],
                                "success_rate": agent_data['success'],
                                "response": response_text
                            })
                            
                            # Add to priority group results
                            priority_group_results.append({
                                "agent_id": agent_data['agent_id'],
                                "agent_name": agent_data['name'],
                                "priority": priority,
                                "accuracy": agent_data['accuracy'],
                                "success_rate": agent_data['success'],
                                "result": result
                            })

                    except Exception as agent_error:
                        logger.error(f"Error with agent {agent_data['agent_id']}: {str(agent_error)}", exc_info=True)
                        continue

                # Add all results from this priority group
                final_results.extend(priority_group_results)
                
                # Update task status
                if priority_group_results:
                    task.status = "in_progress"
                    task.results.extend(priority_group_results)

                logger.info(f"Completed execution of priority {priority} group with {len(priority_group_results)} successful results")

        finally:
            safe_close_connection(conn, cursor)

        # Aggregate results
        aggregated_result = {
            "status": "success",
            "task_id": task.task_id,
            "team_id": team.team_id,
            "results": final_results,
            "conversation_context": conversation_context,
            "final_status": "completed" if final_results else "failed",
            "execution_summary": {
                "total_agents": len(team_agents),
                "successful_executions": len(final_results),
                "priority_groups": sorted_priorities,
                "execution_order": [
                    {
                        "priority": group["priority"],
                        "agents": [f"{group['agent_name']} (ID: {group['agent_id']})" for group in final_results if group["priority"] == group["priority"]]
                    } for group in final_results
                ]
            }
        }

        # Update task status
        task.status = aggregated_result["final_status"]
        task.updated_at = datetime.now()

        return aggregated_result

    except Exception as e:
        logger.error(f"Error in team execution: {str(e)}", exc_info=True)
        task.status = "failed"
        task.updated_at = datetime.now()
        return {
            "status": "error",
            "message": str(e),
            "task_id": task.task_id,
            "team_id": team.team_id
        }

@app.route('/api/ml/agent/<int:agent_id>/initialize', methods=['POST'])
def initialize_agent(agent_id):
    try:
        data = request.get_json()
        use_prod = data.get('use_prod', False)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get agent details with correct column names
        cursor.execute("""
            SELECT id, name, memory_type, foundation_model, status 
            FROM agents WHERE id = %s
        """, (agent_id,))
        agent_data = cursor.fetchone()
        
        if not agent_data:
            return jsonify({
                'status': 'error',
                'message': f'Agent {agent_id} not found'
            }), 404
        
        # Update agent status to active
        cursor.execute(
            "UPDATE agents SET status = 'active' WHERE id = %s",
            (agent_id,)
        )
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Agent {agent_id} initialized successfully',
            'agent': {
                'id': agent_data[0],
                'name': agent_data[1],
                'memory_type': agent_data[2],
                'foundation_model': agent_data[3],
                'status': 'active'
            }
        })
        
    except Exception as e:
        logger.error(f"Error initializing agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/send', methods=['POST'])
@log_execution
def send_agent_message(agent_id):
    """Send a message to an agent and get response from foundation model"""
    conn = None
    cursor = None
    try:
        # Log request data
        request_data = request.get_json()
        logger.info(f"[send_agent_message] Received request data: {request_data}")
        
        message = request_data.get('message')
        team_id = request_data.get('team_id')
        interaction_type = request_data.get('interaction_type', 'direct')

        if not message:
            logger.warning("[send_agent_message] Message is required")
            return jsonify({
                "status": "error",
                "message": "message is required"
            }), 400

        # Initialize agent
        logger.info(f"[send_agent_message] Initializing agent {agent_id} from database...")
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            logger.error(f"[send_agent_message] Agent {agent_id} not found in database")
            return jsonify({"status": "error", "message": "Agent not found"}), 404

        # Log agent details
        logger.info(f"[send_agent_message] Agent details: id={agent.agent_id}, name={agent.name}, memory_type={agent.memory_type}")
        logger.info(f"[send_agent_message] Agent tools: {[t.tool_name for t in agent.tools]}")

        # Set correlation ID for tracking
        conversation_id = str(uuid.uuid4())
        agent.set_correlation_id(conversation_id)
        logger.info(f"[send_agent_message] Set conversation ID: {conversation_id}")

        # Store the message in database
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            logger.info("[send_agent_message] Storing initial message in database...")
            
            # First verify we can insert
            cursor.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
            if not cursor.fetchone():
                raise ValueError(f"Agent {agent_id} not found in database")
            
            # Insert the message
            insert_query = """
                INSERT INTO messages 
                (sender_id, receiver_id, content, interaction_type, conversation_id, team_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            insert_values = (None, agent_id, message, interaction_type, conversation_id, team_id, 'pending')
            
            logger.info(f"[send_agent_message] Executing insert with values: {insert_values}")
            cursor.execute(insert_query, insert_values)
            
            # Get the inserted ID
            message_id = cursor.lastrowid
            logger.info(f"[send_agent_message] Message inserted with ID: {message_id}")
            
            # Verify the insert
            cursor.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
            inserted_message = cursor.fetchone()
            if not inserted_message:
                raise ValueError("Message insert failed - no row found after insert")
                
            conn.commit()
            logger.info("[send_agent_message] Message stored and committed successfully")
            
        except Exception as db_error:
            if conn:
                conn.rollback()
            logger.error(f"[send_agent_message] Database error storing message: {str(db_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Database error: {str(db_error)}"
            }), 500
        finally:
            safe_close_connection(conn, cursor)

        # Process with foundation model
        logger.info("[send_agent_message] Processing message with foundation model...")
        try:
            # Log the messages being sent to the model
            formatted_messages = agent.format_messages_for_llm(message)
            logger.info(f"[send_agent_message] Formatted messages for LLM: {formatted_messages}")
            
            # Log agent state before execution
            logger.info(f"[send_agent_message] Agent state before execution: memories={len(agent.memories)}, tools={len(agent.tools)}")
            
            result = agent.execute_with_tools(message)
            logger.info("[send_agent_message] Foundation model processing complete")
            logger.debug(f"[send_agent_message] Model result: {result}")
            
            if result.get('status') != 'success':
                logger.error(f"[send_agent_message] Model processing failed: {result}")
                return jsonify(result), 500
                
        except Exception as model_error:
            logger.error(f"[send_agent_message] Error processing with foundation model: {str(model_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Model processing error: {str(model_error)}",
                "details": traceback.format_exc()
            }), 500
        
        # Store the model's response
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            logger.info("[send_agent_message] Storing model response in database...")
            update_query = """
                UPDATE messages 
                SET processed_message = %s,
                    model_response = %s,
                    status = 'processed'
                WHERE conversation_id = %s
            """
            update_values = (
                result.get('llm_response', ''),
                json.dumps(result),
                conversation_id
            )
            
            logger.info(f"[send_agent_message] Executing update with values: {update_values}")
            cursor.execute(update_query, update_values)
            
            # Verify the update
            cursor.execute("SELECT * FROM messages WHERE conversation_id = %s", (conversation_id,))
            updated_message = cursor.fetchone()
            if not updated_message or updated_message['status'] != 'processed':
                raise ValueError("Message update failed - no row found or status not updated")
                
            conn.commit()
            logger.info("[send_agent_message] Model response stored and committed successfully")
            
        except Exception as db_error:
            if conn:
                conn.rollback()
            logger.error(f"[send_agent_message] Database error storing model response: {str(db_error)}", exc_info=True)
            return jsonify({
                "status": "error",
                "message": f"Database error: {str(db_error)}",
                "details": traceback.format_exc()
            }), 500
        finally:
            safe_close_connection(conn, cursor)

        response_data = {
            "status": "success",
            "conversation_id": conversation_id,
            "model_response": result.get('llm_response', ''),
            "full_response": result
        }
        logger.info("[send_agent_message] Successfully completed message processing")
        return jsonify(response_data)

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"[send_agent_message] Unhandled error: {str(e)}",
            extra={
                'agent_id': agent_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({
            "status": "error",
            "message": f"Error processing message: {str(e)}",
            "details": traceback.format_exc()
        }), 500
    finally:
        safe_close_connection(conn, cursor)

@app.route('/api/ml/agent/<int:agent_id>/response/<conversation_id>', methods=['GET'])
@log_execution
def get_agent_response(agent_id, conversation_id):
    """Get the foundation model's response for a specific conversation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        try:
            cursor.execute(
                """SELECT content, processed_message, model_response, status
                FROM messages 
                WHERE conversation_id = %s AND receiver_id = %s""",
                (conversation_id, agent_id)
            )
            message = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not message:
            return jsonify({
                "status": "error",
                "message": "Message not found"
            }), 404

        if message['status'] != 'processed':
            return jsonify({
                "status": "pending",
                "message": "Message is still being processed"
            })

        return jsonify({
            "status": "success",
            "original_message": message['content'],
            "model_response": message['processed_message'],
            "full_response": json.loads(message['model_response']) if message['model_response'] else None
        })

    except Exception as e:
        logger.error(
            f"Error in get_agent_response: {str(e)}",
            extra={
                'agent_id': agent_id,
                'conversation_id': conversation_id,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/ml/agent/<int:agent_id>/receive/<int:interaction_id>', methods=['POST'])
def receive_message(agent_id, interaction_id):
    """Process a received message"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get message details
        cursor.execute("""
            SELECT id, sender_id, receiver_id, content, processed_message,
                   interaction_type, status, created_at
            FROM messages 
            WHERE id = %s AND receiver_id = %s
        """, (interaction_id, agent_id))
        
        message = cursor.fetchone()
        if not message:
            return jsonify({
                'status': 'error',
                'message': 'Message not found'
            }), 404
        
        # Convert datetime objects to strings for JSON serialization
        if message:
            if message.get('created_at'):
                if isinstance(message['created_at'], datetime):
                    message['created_at'] = message['created_at'].isoformat()
                else:
                    message['created_at'] = str(message['created_at'])
        
        # Update message status and processed content
        cursor.execute("""
            UPDATE messages 
            SET status = 'processed',
                processed_message = content
            WHERE id = %s
        """, (interaction_id,))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': message
        })
        
    except Exception as e:
        logger.error(f"Error receiving message: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/workflow', methods=['POST'])
def start_agent_workflow(agent_id):
    """Start a multi-agent workflow"""
    try:
        workflow_data = request.json
        if not workflow_data:
            return jsonify({
                "status": "error",
                "message": "Workflow data is required"
            }), 400

        # Initialize source agent
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            return jsonify({"status": "error", "message": "Source agent not found"}), 404

        # Start workflow
        result = agent.start_workflow(workflow_data)
        return jsonify(result)

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def initialize_agent_from_db(agent_id: int) -> Agent:
    """Helper function to initialize an agent from database"""
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get agent details including team_id
        cursor.execute("""
            SELECT a.*, ta.team_id 
            FROM agents a
            LEFT JOIN team_agents ta ON a.id = ta.agent_id
            WHERE a.id = %s
        """, (agent_id,))
        agent_data = cursor.fetchone()  # Ensure we fetch the result
        
        # Consume any remaining results
        while cursor.fetchone() is not None:
            pass
        
        if not agent_data:
            logger.error(f"Agent {agent_id} not found in database")
            return None

        # Create agent instance
        agent = Agent(
            agent_data["id"],
            agent_data["name"],
            agent_data["memory_type"],
            agent_data["foundation_model"],
            agent_data.get("team_id")  # Now getting team_id from join
        )

        # Close the current cursor before creating new ones
        cursor.close()
        cursor = None

        # Load agent's memories with a new cursor
        memory_cursor = conn.cursor(dictionary=True)
        try:
            memory_cursor.execute("""
                SELECT * FROM agent_memory 
                WHERE agent_id = %s 
                ORDER BY updated_at DESC
            """, (agent_id,))
            agent.memories = memory_cursor.fetchall()  # Fetch all results at once
            
            # Consume any remaining results
            while memory_cursor.fetchone() is not None:
                pass
                
            logger.info(f"Loaded {len(agent.memories)} memories for agent {agent_id}")
        except Exception as e:
            logger.error(f"Error loading memories for agent {agent_id}: {e}", exc_info=True)
        finally:
            memory_cursor.close()

        # Get agent's tools with a new cursor
        tools_cursor = conn.cursor(dictionary=True)
        try:
            tools_cursor.execute("""
                SELECT t.* 
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = %s
            """, (agent_id,))
            
            tools_data = tools_cursor.fetchall()  # Fetch all results at once
            
            # Consume any remaining results
            while tools_cursor.fetchone() is not None:
                pass
                
            logger.info(f"Found {len(tools_data)} tools for agent {agent_id}")
            
            for tool_data in tools_data:
                try:
                    tool = create_tool(tool_data)
                    agent.add_tool(tool)
                    logger.info(f"Added tool {tool_data['tool_name']} to agent {agent_id}")
                except ValueError as e:
                    logger.error(f"Failed to create tool for agent {agent_id}: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error creating tool for agent {agent_id}: {e}", exc_info=True)

            if not agent.tools:
                logger.warning(f"No tools were successfully loaded for agent {agent_id}")
                
        except Exception as e:
            logger.error(f"Error loading tools for agent {agent_id}: {e}", exc_info=True)
        finally:
            tools_cursor.close()

        return agent

    except Exception as e:
        logger.error(f"Error initializing agent {agent_id}: {e}", exc_info=True)
        return None
    finally:
        if cursor:
            try:
                # Consume any remaining results before closing
                while cursor and cursor.fetchone() is not None:
                    pass
                cursor.close()
            except Exception as e:
                logger.error(f"Error closing cursor: {e}", exc_info=True)
        if conn:
            conn.close()

# Error handlers with logging
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(
        f"404 Not Found: {request.url}",
        extra={'path': request.path, 'method': request.method}
    )
    return jsonify({"status": "error", "message": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(
        f"500 Internal Server Error: {str(error)}",
        extra={
            'path': request.path,
            'method': request.method,
            'error': str(error),
            'traceback': traceback.format_exc()
        }
    )
    return jsonify({"status": "error", "message": "Internal server error"}), 500

@app.route('/api/ml/tools', methods=['GET'])
def get_tools():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT id, tool_name, description, type FROM tools")
        tools = cursor.fetchall()
        
        return jsonify({
            'status': 'success',
            'tools': tools
        })
        
    except Exception as e:
        logger.error(f"Error fetching tools: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/tools/<int:tool_id>', methods=['GET', 'PUT'])
def manage_tool(tool_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute(
                "SELECT id, tool_name, description, type FROM tools WHERE id = %s",
                (tool_id,)
            )
            tool = cursor.fetchone()
            
            if not tool:
                return jsonify({
                    'status': 'error',
                    'message': 'Tool not found'
                }), 404
                
            return jsonify({
                'status': 'success',
                'tool': tool
            })
            
        elif request.method == 'PUT':
            data = request.get_json()
            
            cursor.execute(
                """UPDATE tools 
                SET tool_name = %s, description = %s, type = %s 
                WHERE id = %s""",
                (data['tool_name'], data['description'], data['type'], tool_id)
            )
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Tool updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error managing tool {tool_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/tools', methods=['GET', 'POST'])
def manage_agent_tools(agent_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        if request.method == 'GET':
            cursor.execute("""
                SELECT t.id, t.tool_name, t.description, t.type
                FROM tools t
                JOIN agent_tools at ON t.id = at.tool_id
                WHERE at.agent_id = %s
            """, (agent_id,))
            tools = cursor.fetchall()
            
            return jsonify({
                'status': 'success',
                'tools': tools
            })
            
        elif request.method == 'POST':
            data = request.get_json()
            tool_ids = data.get('tool_ids', [])
            
            # First remove existing tools
            cursor.execute(
                "DELETE FROM agent_tools WHERE agent_id = %s",
                (agent_id,)
            )
            
            # Add new tools
            for tool_id in tool_ids:
                cursor.execute(
                    """INSERT INTO agent_tools (agent_id, tool_id)
                    VALUES (%s, %s)""",
                    (agent_id, tool_id)
                )
                
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Agent tools updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error managing tools for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/tool/<int:tool_id>', methods=['POST', 'DELETE'])
def manage_single_agent_tool(agent_id, tool_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            cursor.execute(
                """INSERT INTO agent_tools (agent_id, tool_id)
                VALUES (%s, %s)""",
                (agent_id, tool_id)
            )
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Tool added to agent successfully'
            })
            
        elif request.method == 'DELETE':
            cursor.execute(
                """DELETE FROM agent_tools 
                WHERE agent_id = %s AND tool_id = %s""",
                (agent_id, tool_id)
            )
            conn.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Tool removed from agent successfully'
            })
            
    except Exception as e:
        logger.error(f"Error managing tool {tool_id} for agent {agent_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/agent/<int:agent_id>/execute_all', methods=['POST'])
@log_execution
def execute_all_tools(agent_id):
    """Execute a command with all tools available to the agent"""
    try:
        data = request.get_json()
        if not data or 'command' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Command is required'
            }), 400

        # Initialize agent from database
        agent = initialize_agent_from_db(agent_id)
        if not agent:
            return jsonify({
                'status': 'error',
                'message': 'Agent not found'
            }), 404

        # Set correlation ID for tracking
        agent.set_correlation_id(str(uuid.uuid4()))

        # Execute command with all tools
        result = agent.execute_with_tools(data['command'])
        
        # Convert any non-serializable objects to strings
        def serialize_value(value):
            if isinstance(value, (datetime, decimal.Decimal)):
                return str(value)
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_value(item) for item in value]
            return value

        # Clean the result for JSON serialization
        serializable_result = serialize_value(result)
        
        if result.get('status') == 'error':
            return jsonify(serializable_result), 500

        return jsonify(serializable_result)

    except Exception as e:
        logger.error(
            f"Error executing command with all tools: {str(e)}",
            extra={
                'agent_id': agent_id,
                'error_msg': str(e),
                'traceback': traceback.format_exc()
            }
        )
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/ml/agent-memory', methods=['POST'])
@log_execution
def create_agent_memory():
    """Create a new memory for an agent"""
    try:
        data = request.json
        required_fields = ['agent_id', 'memory_type']
        if not all(field in data for field in required_fields):
            logger.warning(f"Missing required fields in request: {data}")
            return jsonify({
                "status": "error",
                "message": f"Missing required fields: {', '.join(required_fields)}"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Verify agent exists
            cursor.execute("SELECT id FROM agents WHERE id = %s", (data['agent_id'],))
            if not cursor.fetchone():
                logger.warning(f"Agent {data['agent_id']} not found")
                return jsonify({
                    "status": "error",
                    "message": f"Agent with id {data['agent_id']} not found"
                }), 404

            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_memory (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    agent_id INT NOT NULL,
                    memory_type VARCHAR(50) NOT NULL,
                    start_prompt TEXT,
                    end_prompt TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (agent_id) REFERENCES agents(id)
                )
            """)

            # Insert memory
            insert_query = """
                INSERT INTO agent_memory 
                (agent_id, memory_type, start_prompt, end_prompt, context)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                data['agent_id'],
                data['memory_type'],
                data.get('start_prompt'),
                data.get('end_prompt'),
                data.get('context')
            ))
            conn.commit()
            memory_id = cursor.lastrowid

            # Fetch the created memory
            cursor.execute("SELECT * FROM agent_memory WHERE id = %s", (memory_id,))
            memory = cursor.fetchone()

            logger.info(f"Created memory for agent {data['agent_id']}: {memory}")
            return jsonify({
                "status": "success",
                "memory": memory
            })

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.error(f"Error creating agent memory: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Failed to create memory: {str(e)}"
        }), 500

@app.route('/api/tools/<int:tool_id>', methods=['GET'])
def get_tool(tool_id):
    """Get details of a specific tool"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, tool_name, description, type, hostname, auth_method
            FROM tools 
            WHERE id = %s
        """, (tool_id,))
        
        tool = cursor.fetchone()
        
        if not tool:
            return jsonify({
                'status': 'error',
                'message': 'Tool not found'
            }), 404
            
        return jsonify({
            'status': 'success',
            'tool_name': tool['tool_name'],
            'tool_type': tool['type'],
            'hostname': tool['hostname'],
            'auth_method': tool['auth_method']
        })
        
    except Exception as e:
        logger.error(f"Error fetching tool {tool_id}: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Initialize database tables
def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        conn.commit()
        logger.info("Database tables initialized successfully")
        
    except mysql.connector.Error as e:
        logger.error(f"Database error during initialization: {e}", exc_info=True)
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Initialize database on startup
# init_db()

@app.route('/api/debug/db-contents', methods=['GET'])
def get_db_contents():
    """Debug endpoint to check database contents"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        tables = ['agents', 'agent_memory', 'messages', 'tools', 'agent_tools']
        contents = {}
        
        for table in tables:
            try:
                cursor.execute(f"SELECT * FROM {table}")
                contents[table] = cursor.fetchall()
                # Convert datetime objects to strings for JSON serialization
                if contents[table]:
                    for row in contents[table]:
                        for key, value in row.items():
                            if isinstance(value, datetime):
                                row[key] = value.isoformat()
                logger.info(f"Found {len(contents[table])} rows in {table}")
            except Exception as e:
                logger.error(f"Error fetching from {table}: {str(e)}")
                contents[table] = {"error": str(e)}
        
        return jsonify({
            "status": "success",
            "database_contents": contents
        })
        
    except Exception as e:
        logger.error(f"Error checking database contents: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/debug/db-connection', methods=['GET'])
def check_db_connection():
    """Debug endpoint to verify database connection"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try a simple query
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        
        # Get database version
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        
        # Get table counts
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_ROWS
            FROM information_schema.tables
            WHERE TABLE_SCHEMA = %s
        """, (db_config['database'],))
        table_counts = cursor.fetchall()
        
        return jsonify({
            "status": "success",
            "connection": "active",
            "database": db_config['database'],
            "version": version[0] if version else None,
            "table_counts": dict(table_counts)
        })
        
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@app.route('/api/ml/team/execute', methods=['POST'])
@log_execution
def execute_team_task():
    """Execute a task using a team of agents"""
    conn = None
    cursor = None
    start_time = datetime.now()
    correlation_id = None
    
    try:
        data = request.json
        if not data:
            return jsonify({
                "status": "error",
                "message": "Request body is required"
            }), 400

        # Validate required fields
        required_fields = ['content', 'userId', 'sessionId', 'context']
        if not all(field in data for field in required_fields):
            return jsonify({
                "status": "error",
                "message": f"Missing required fields. Required: {required_fields}"
            }), 400

        # Get team_id from context
        team_id = data['context'].get('team_id')
        team_config = data['context'].get('team_config')
        if not team_id or not team_config:
            return jsonify({
                "status": "error",
                "message": "team_id and team_config are required in context"
            }), 400

        logger.info(f"[TEAM EXECUTION] Processing request for team_id: {team_id}")
        logger.debug(f"[TEAM CONFIG] {json.dumps(team_config, indent=2)}")

        # Initialize database connection
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify team exists
        cursor.execute("SELECT * FROM teams WHERE id = %s", (team_id,))
        team_record = cursor.fetchone()
        if not team_record:
            logger.error(f"[TEAM ERROR] Team {team_id} not found in database")
            # Create team if it doesn't exist
            try:
                cursor.execute("""
                    INSERT INTO teams (id, name, created_at, updated_at)
                    VALUES (%s, %s, NOW(), NOW())
                """, (team_id, team_config['name']))
                conn.commit()
                logger.info(f"[TEAM CREATED] Created new team with ID {team_id}")
            except Exception as e:
                logger.error(f"[TEAM ERROR] Failed to create team: {str(e)}")
                return jsonify({
                    "status": "error",
                    "message": f"Failed to create team: {str(e)}"
                }), 500

        # Verify and create team members
        # First check for existing team agents
        cursor.execute("""
            SELECT ta.agent_id, ta.priority, ta.accuracy, ta.success, a.name
            FROM team_agents ta
            JOIN agents a ON ta.agent_id = a.id
            WHERE ta.team_id = %s
        """, (team_id,))
        existing_agents = cursor.fetchall()
        
        if existing_agents:
            logger.info(f"[TEAM MEMBERS] Found {len(existing_agents)} existing agents for team {team_id}")
            # Use existing agents instead of creating new ones
            team_config['members'] = [
                {
                    "agent_id": agent['agent_id'],
                    "name": agent['name'],
                    "priority": agent['priority'] or 1,
                    "accuracy_threshold": agent['accuracy'] / 100 if agent['accuracy'] else 0.8,
                    "success_rate": agent['success'] / 100 if agent['success'] else 0.9,
                    "role": "processor"
                }
                for agent in existing_agents
            ]
        else:
            # Only create new agents if none exist
            members = team_config.get('members', [])
            logger.info(f"[TEAM MEMBERS] Processing {len(members)} members for team {team_id}")
            
            for member in members:
                agent_id = member.get('agent_id')
                if not agent_id:
                    continue

                # Check if agent exists
                cursor.execute("SELECT id FROM agents WHERE id = %s", (agent_id,))
                agent_record = cursor.fetchone()
                if not agent_record:
                    # Create agent if it doesn't exist
                    try:
                        cursor.execute("""
                            INSERT INTO agents (id, name, description, status)
                            VALUES (%s, %s, %s, 'active')
                            AS new_agent
                            ON DUPLICATE KEY UPDATE
                            name = new_agent.name,
                            status = 'active'
                        """, (agent_id, f"Agent_{agent_id}", "Auto-created agent"))
                        logger.info(f"[AGENT CREATED] Created new agent with ID {agent_id}")
                    except Exception as e:
                        logger.error(f"[AGENT ERROR] Failed to create agent {agent_id}: {str(e)}")
                        continue

                # Add agent to team if not already added
                try:
                    cursor.execute("""
                        INSERT INTO team_agents (team_id, agent_id, priority, accuracy, success)
                        VALUES (%s, %s, %s, %s, %s)
                        AS new_team_agent
                        ON DUPLICATE KEY UPDATE
                        priority = new_team_agent.priority,
                        accuracy = new_team_agent.accuracy,
                        success = new_team_agent.success
                    """, (
                        team_id,
                        agent_id,
                        member.get('priority', 1),
                        member.get('accuracy_threshold', 0.8) * 100,  # Convert to percentage
                        member.get('success_rate', 0.9) * 100  # Convert to percentage
                    ))
                    logger.info(f"[TEAM MEMBER ADDED] Added/Updated agent {agent_id} to team {team_id}")
                except Exception as e:
                    logger.error(f"[TEAM MEMBER ERROR] Failed to add agent {agent_id} to team: {str(e)}")

        conn.commit()

        # 1. Team Task Initialization
        correlation_id = str(uuid.uuid4())
        task = {
            'description': data['content'],
            'requirements': {
                'user_id': data['userId'],
                'session_id': data['sessionId'],
                'conversation_settings': data['context'].get('conversation_settings', {}),
                'conversation_history': data['context'].get('conversation_history', []),
                'documents': data['context'].get('documents', [])
            }
        }
        task_id = store_team_task(cursor, team_id, task, correlation_id)
        
        # Create workflow record
        workflow_id = create_workflow_record(cursor, team_id, task_id, correlation_id)
        
        # 2. Agent Priority Organization
        agents = get_team_agents_ordered(cursor, team_id)
        logger.info(f"[TEAM AGENTS] Found {len(agents)} agents for team {team_id}")
        logger.debug(f"[TEAM AGENTS] {json.dumps(agents, indent=2)}")
        
        if not agents:
            error_msg = f"No agents found for team {team_id}"
            logger.error(f"[TEAM ERROR] {error_msg}")
            return jsonify({
                "status": "error",
                "message": error_msg
            }), 404

        # Group agents by priority for potential parallel execution
        priority_groups = group_agents_by_priority(agents)
        
        # 3. Agent Execution & 4. Tool Execution
        all_responses = []
        for priority_level, priority_agents in priority_groups.items():
            # Create workflow steps for this priority group
            step_ids = create_workflow_steps(cursor, workflow_id, priority_agents)
            
            # Execute agents in parallel within priority group
            priority_responses = execute_priority_group(
                priority_agents, 
                step_ids,
                task,
                correlation_id
            )
            all_responses.extend(priority_responses)
            
            # Update workflow steps status
            update_workflow_steps_status(cursor, step_ids, 'completed')
            
        # 5. Response Aggregation
        final_response = aggregate_team_responses(all_responses)
        
        # 6. Task Completion
        update_workflow_status(cursor, workflow_id, 'completed')
        
        # Commit all changes
        conn.commit()
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds())
        
        # Format final response according to expected structure
        response = {
            "status": final_response['status'],
            "team": {
                "team_id": str(team_id),
                "name": team_config['name'],
                "description": team_config['description'],
                "members": [
                    {
                        "agent_id": result['agent_id'],
                        "priority": result['priority'],
                        "accuracy_threshold": result['accuracy'],
                        "success_rate": result['success_rate'],
                        "current_task": None,
                        "results": result['result']['tool_results']
                    }
                    for result in final_response['results']
                ],
                "tasks": [
                    {
                        "task_id": task_id,
                        "description": task['description'],
                        "requirements": task['requirements'],
                        "status": final_response['final_status'],
                        "results": final_response['tool_results'],
                        "created_at": start_time.isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                ],
                "created_at": start_time.isoformat(),
                "updated_at": datetime.now().isoformat()
            },
            "result": {
                "status": final_response['final_status'],
                "task_id": task_id,
                "team_id": str(team_id),
                "results": final_response['results'],
                "conversation_context": final_response['conversation_context'],
                "final_status": final_response['final_status'],
                "execution_summary": final_response['execution_summary']
            },
            "correlation_id": correlation_id,
            "workflow_id": workflow_id,
            "processing_time_seconds": processing_time
        }
        
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in execute_team_task: {str(e)}", 
                    extra={"correlation_id": correlation_id})
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": f"Internal server error: {str(e)}"
        }), 500
        
    finally:
        safe_close_connection(conn, cursor)

@app.route('/api/ml/team/history', methods=['GET'])
def get_team_history():
    """Get history of team messages and tasks"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get optional query parameters
        team_id = request.args.get('team_id')
        status = request.args.get('status')
        limit = request.args.get('limit', 100)
        
        # Build query
        query = "SELECT * FROM team_messages WHERE 1=1"
        params = []
        
        if team_id:
            query += " AND team_id = %s"
            params.append(team_id)
            
        if status:
            query += " AND status = %s"
            params.append(status)
            
        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(int(limit))
        
        # Execute query
        cursor.execute(query, tuple(params))
        history = cursor.fetchall()
        
        # Convert datetime objects to strings
        for record in history:
            record['created_at'] = record['created_at'].isoformat() if record['created_at'] else None
            record['updated_at'] = record['updated_at'].isoformat() if record['updated_at'] else None
        
        return jsonify({
            "status": "success",
            "history": history
        })
        
    except Exception as e:
        logger.error(f"Error fetching team history: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        safe_close_connection(conn, cursor)

@app.route('/api/ml/conversation/store', methods=['POST'])
@log_execution
def store_conversation():
    """Store conversation history in the database"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        required_fields = ['conversation_id', 'content', 'metadata']
        if not all(field in data for field in required_fields):
            return jsonify({'error': f'Missing required fields. Required: {required_fields}'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Store the conversation
            insert_query = """
                INSERT INTO conversations (
                    conversation_id,
                    content,
                    metadata,
                    created_at
                ) VALUES (%s, %s, %s, NOW()) AS new_data
                ON DUPLICATE KEY UPDATE
                    content = new_data.content,
                    metadata = new_data.metadata,
                    updated_at = NOW()
            """
            
            cursor.execute(insert_query, (
                data['conversation_id'],
                json.dumps(data['content']),
                json.dumps(data['metadata'])
            ))
            
            conn.commit()

            logger.info(f"Stored conversation {data['conversation_id']}")
            return jsonify({
                'status': 'success',
                'message': 'Conversation stored successfully',
                'conversation_id': data['conversation_id']
            })

        finally:
            safe_close_connection(conn, cursor)

    except Exception as e:
        logger.error(f"Error storing conversation: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to store conversation: {str(e)}'
        }), 500

@app.route('/api/agent-interactions', methods=['GET'])
def get_agent_interactions():
    """Get agent interactions from messages table"""
    try:
        team_id = request.args.get('team_id')
        source = request.args.get('source')
        target = request.args.get('target')
        conversation_id = request.args.get('conversation_id')
        
        logger.info(f"[get_agent_interactions] Request params: team_id={team_id}, source={source}, target={target}, conversation_id={conversation_id}")
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Base query joining with agents table to get names
        query = """
            SELECT DISTINCT
                m.id,
                m.conversation_id,
                COALESCE(sa.name, 'OpenAI') as source_agent,
                COALESCE(ra.name, 'OpenAI') as target_agent,
                m.interaction_type,
                m.status,
                m.created_at as timestamp,
                m.content,
                m.processed_message,
                m.model_response
            FROM messages m
            LEFT JOIN agents sa ON m.sender_id = sa.id
            LEFT JOIN agents ra ON m.receiver_id = ra.id
            WHERE 1=1
        """
        params = []
        
        # Add filters
        if team_id:
            query += " AND m.team_id = %s"
            params.append(int(team_id))
        
        if source:
            query += " AND m.sender_id = %s"
            params.append(int(source))
            
        if target:
            query += " AND m.receiver_id = %s"
            params.append(int(target))
            
        if conversation_id:
            query += " AND m.conversation_id = %s"
            params.append(conversation_id)
            
        query += " ORDER BY m.created_at DESC"
        
        logger.info(f"[get_agent_interactions] Executing query: {query}")
        logger.info(f"[get_agent_interactions] Query params: {params}")
        
        cursor.execute(query, params)
        interactions = cursor.fetchall()
        logger.info(f"[get_agent_interactions] Found {len(interactions)} interactions")
        
        # Convert datetime objects to strings and ensure all fields are JSON serializable
        formatted_interactions = []
        for interaction in interactions:
            formatted_interaction = {}
            for key, value in interaction.items():
                if isinstance(value, datetime):
                    formatted_interaction[key] = value.isoformat()
                else:
                    formatted_interaction[key] = value
            formatted_interactions.append(formatted_interaction)
        
        logger.info(f"[get_agent_interactions] Returning {len(formatted_interactions)} formatted interactions")
        return jsonify(formatted_interactions)
        
    except Exception as e:
        logger.error(f"Error fetching agent interactions: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# Import routes
from app.routes import agent_bp, tool_bp, team_bp

# Register routes
app.register_blueprint(agent_bp)
app.register_blueprint(tool_bp)
app.register_blueprint(team_bp)

# ... existing code ...

if __name__ == '__main__':
    app.run(port=5000, debug=True)