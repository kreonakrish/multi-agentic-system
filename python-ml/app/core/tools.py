import logging
import requests
import pandas as pd
from io import StringIO
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tag import pos_tag
from app.utils.logger import logger
import json
import re
import time
import os
from app.rag.core.factory import RAGFactory
from app.rag.core.config import RAGConfig
from app.rag.core.pipeline import RAGPipeline
from app.config.openai_config import get_openai_client
from datetime import datetime

class Tool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 description: str = ""):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.hostname = hostname
        self.username = username
        self._password = password  # Note the protected attribute
        self.auth_method = auth_method
        self.description = description
        self._is_connected = False
        self.logger = logging.getLogger(__name__)

    @property
    def is_connected(self) -> bool:
        """Check if tool is connected"""
        return self._is_connected

    def connect(self) -> bool:
        """Establish connection to the tool"""
        try:
            self.logger.info(f"[TOOL] Connecting to {self.tool_name}")
            # Implement actual connection logic in subclasses
            self._is_connected = True
            return True
        except Exception as e:
            self.logger.error(f"[TOOL] Failed to connect to {self.tool_name}: {str(e)}")
            self._is_connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the tool"""
        try:
            self.logger.info(f"[TOOL] Disconnecting from {self.tool_name}")
            self._is_connected = False
        except Exception as e:
            self.logger.error(f"[TOOL] Error disconnecting from {self.tool_name}: {str(e)}")

    def get_default_response(self, command: str) -> Dict[str, Any]:
        """Get a structured default response"""
        return {
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "tool_type": self.__class__.__name__,
            "hostname": self.hostname,
            "auth_method": self.auth_method,
            "description": self.description,
            "command": command,
            "status": "success",
            "message": f"Tool {self.tool_name} ({self.__class__.__name__}) executed successfully",
            "execution_time": None,  # Will be set by execute method
            "correlation_id": None,  # Will be set by execute method if provided
            "validation_result": None  # Will be set if validation is performed
        }

    @abstractmethod
    def execute(self, command: str, correlation_id: str = None) -> Dict[str, Any]:
        """Execute a command using the tool"""
        pass

    def validate_response(self, response: Dict[str, Any], end_prompt: str = None) -> Dict[str, Any]:
        """Validate tool response using LLM if needed"""
        if not end_prompt:
            return response
            
        try:
            self.logger.info("[TOOL] Starting response validation")
            
            validation_prompt = f"""Please validate the following tool execution result:
{json.dumps(response, indent=2)}

Validation criteria:
1. Check if the tool provided relevant information
2. Verify if any critical errors occurred
3. Assess if additional tool executions are needed
4. Evaluate the quality and completeness of the response

{end_prompt}

Please provide a detailed validation report in JSON format with the following structure:
{{
    "valid": boolean,
    "validation_details": {{
        "relevant_information_provided": boolean,
        "critical_errors_found": boolean,
        "additional_tools_needed": boolean,
        "quality_assessment": string
    }},
    "issues": [string],
    "recommendations": [string]
}}"""

            # Here you would call your LLM service
            # For now, return a default validation
            validation_result = {
                "valid": True,
                "validation_details": {
                    "relevant_information_provided": True,
                    "critical_errors_found": False,
                    "additional_tools_needed": False,
                    "quality_assessment": "Response meets requirements"
                },
                "issues": [],
                "recommendations": []
            }
            
            response["validation_result"] = validation_result
            return response
            
        except Exception as e:
            self.logger.error(f"[TOOL] Error validating response: {str(e)}")
            response["validation_warning"] = str(e)
            return response

    def _sanitize_directory_name(self, name: str) -> str:
        """
        Sanitize directory name by:
        1. Converting to lowercase
        2. Replacing spaces with underscores
        3. Removing special characters
        4. Ensuring it's a valid directory name
        """
        # Convert to lowercase
        name = name.lower()
        
        # Replace spaces with underscores
        name = name.replace(' ', '_')
        
        # Remove any special characters except underscores and hyphens
        name = re.sub(r'[^a-z0-9_-]', '', name)
        
        # Ensure the name starts with a letter or number
        if not name[0].isalnum():
            name = 'tool_' + name
            
        return name

class DatabaseTool(Tool):
    """Tool for database operations"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 database: str, port: Optional[int] = None,
                 description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.database = database
        self.port = port or 3306

    def execute(self, command: str, correlation_id: str = None) -> Dict[str, Any]:
        """Execute a database command"""
        start_time = time.time()
        try:
            if not self.is_connected and not self.connect():
                raise Exception("Failed to connect to database")

            self.logger.info(f"Executing database command on {self.database}")
            response = self.get_default_response(command)
            
            # Execute the actual database command here
            query_type = self._get_query_type(command)
            
            response.update({
                "database_specific": {
                    "database": self.database,
                    "port": self.port,
                    "query_type": query_type,
                    "affected_rows": 0  # Replace with actual count in implementation
                }
            })
            
            elapsed_time = time.time() - start_time
            response["execution_time"] = elapsed_time
            self.logger.info(f"Database command executed successfully in {elapsed_time:.2f} seconds")
            
            return self.validate_response(response, correlation_id)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Database execution error after {elapsed_time:.2f} seconds: {str(e)}")
            return {
                "status": "error",
                "message": f"Database execution error: {str(e)}",
                "execution_time": elapsed_time
            }

    def _get_query_type(self, command: str) -> str:
        """Determine the type of SQL query"""
        command = command.strip().upper()
        if command.startswith('SELECT'):
            return 'SELECT'
        elif command.startswith('INSERT'):
            return 'INSERT'
        elif command.startswith('UPDATE'):
            return 'UPDATE'
        elif command.startswith('DELETE'):
            return 'DELETE'
        return 'UNKNOWN'

class APITool(Tool):
    """Tool for API operations"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 api_version: str = 'v1', timeout: int = 30,
                 description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.api_version = api_version
        self.timeout = timeout

    def execute(self, command: str, correlation_id: str = None) -> Dict[str, Any]:
        """Execute an API command"""
        start_time = time.time()
        try:
            self.logger.info(f"Executing API command on {self.hostname}")
            
            # Get HTTP method and prepare request
            method = self._get_http_method(command)
            endpoint = f"{self.hostname}/api/{self.api_version}"
            
            # Execute the actual API call here
            # For now, just simulate the call
            
            response = self.get_default_response(command)
            response.update({
                "api_specific": {
                    "endpoint": endpoint,
                    "method": method,
                    "timeout": self.timeout,
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._password}" if self.auth_method == "bearer" else None
                    }
                }
            })
            
            elapsed_time = time.time() - start_time
            response["execution_time"] = elapsed_time
            self.logger.info(f"API command executed successfully in {elapsed_time:.2f} seconds")
            
            return self.validate_response(response, correlation_id)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"API execution error after {elapsed_time:.2f} seconds: {str(e)}")
            return {
                "status": "error",
                "message": f"API execution error: {str(e)}",
                "execution_time": elapsed_time
            }

    def _get_http_method(self, command: str) -> str:
        """Determine the HTTP method from command"""
        command = command.strip().upper()
        if command.startswith('GET'):
            return 'GET'
        elif command.startswith('POST'):
            return 'POST'
        elif command.startswith('PUT'):
            return 'PUT'
        elif command.startswith('DELETE'):
            return 'DELETE'
        return 'GET'  # Default to GET

class WebServiceTool(Tool):
    """Tool for web service operations"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 service_type: str = 'REST', timeout: int = 30,
                 description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.service_type = service_type
        self.timeout = timeout

    def execute(self, command: str, correlation_id: str = None) -> Dict[str, Any]:
        """Execute a web service command"""
        start_time = time.time()
        try:
            self.logger.info(f"Executing web service command on {self.hostname}")
            
            # Execute the actual web service call here
            # For now, just simulate the call
            
            response = self.get_default_response(command)
            response.update({
                "service_specific": {
                    "service_endpoint": f"{self.hostname}/service",
                    "service_type": self.service_type,
                    "timeout": self.timeout,
                    "headers": {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._password}" if self.auth_method == "bearer" else None
                    }
                }
            })
            
            elapsed_time = time.time() - start_time
            response["execution_time"] = elapsed_time
            self.logger.info(f"Web service command executed successfully in {elapsed_time:.2f} seconds")
            
            return self.validate_response(response, correlation_id)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Web service execution error after {elapsed_time:.2f} seconds: {str(e)}")
            return {
                "status": "error",
                "message": f"Web service execution error: {str(e)}",
                "execution_time": elapsed_time
            }

class PythonTool(Tool):
    """Tool for Python code execution"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 python_version: str = "3.8", description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.python_version = python_version

    def execute(self, command: str, correlation_id: str = None) -> Dict[str, Any]:
        """Execute Python code"""
        start_time = time.time()
        try:
            self.logger.info(f"Executing Python command with version {self.python_version}")
            
            # Execute the actual Python code here
            # For now, just simulate the execution
            
            response = self.get_default_response(command)
            response.update({
                "python_specific": {
                    "version": self.python_version,
                    "execution_mode": "script",
                    "environment": "isolated",
                    "imports": self._extract_imports(command)
                }
            })
            
            elapsed_time = time.time() - start_time
            response["execution_time"] = elapsed_time
            self.logger.info(f"Python command executed successfully in {elapsed_time:.2f} seconds")
            
            return self.validate_response(response, correlation_id)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Python execution error after {elapsed_time:.2f} seconds: {str(e)}")
            return {
                "status": "error",
                "message": f"Python execution error: {str(e)}",
                "execution_time": elapsed_time
            }

    def _extract_imports(self, command: str) -> List[str]:
        """Extract import statements from Python code"""
        imports = []
        for line in command.split('\n'):
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                imports.append(line.strip())
        return imports

class ReactTool(Tool):
    """Tool for React component operations"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 react_version: str = "18.0", description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.react_version = react_version

    def execute(self, command: str, correlation_id: str = None) -> Dict[str, Any]:
        """Execute React component operations"""
        start_time = time.time()
        try:
            self.logger.info(f"Executing React command with version {self.react_version}")
            
            # Execute the actual React component operation here
            # For now, just simulate the operation
            
            response = self.get_default_response(command)
            response.update({
                "react_specific": {
                    "version": self.react_version,
                    "component_type": "functional",
                    "environment": "development",
                    "dependencies": self._extract_dependencies(command)
                }
            })
            
            elapsed_time = time.time() - start_time
            response["execution_time"] = elapsed_time
            self.logger.info(f"React command executed successfully in {elapsed_time:.2f} seconds")
            
            return self.validate_response(response, correlation_id)
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"React execution error after {elapsed_time:.2f} seconds: {str(e)}")
            return {
                "status": "error",
                "message": f"React execution error: {str(e)}",
                "execution_time": elapsed_time
            }

    def _extract_dependencies(self, command: str) -> List[str]:
        """Extract import/require statements from React code"""
        dependencies = []
        for line in command.split('\n'):
            if line.strip().startswith('import ') or line.strip().startswith('require('):
                dependencies.append(line.strip())
        return dependencies

class GitHubTool(Tool):
    def __init__(self, tool_id: int, tool_name: str, hostname: str, username: str, password: str, auth_method: str, description: str):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.logger = logging.getLogger(__name__)
        self.max_rows = 100  # Maximum number of rows to return
        # Initialize RAG pipeline
        self.rag_pipeline = RAGFactory.create_pipeline(RAGConfig())

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
                df = pd.read_csv(StringIO(response.text))
                
                # Convert DataFrame to list of dictionaries
                data = df.to_dict('records')
                
                # Limit the number of rows if specified
                if self.max_rows and len(data) > self.max_rows:
                    data = data[:self.max_rows]
                
                # Format data for visualization if it's NFL team data
                visualization_data = None
                if 'nfl-favorite-team' in dataset_name.lower():
                    # Calculate average scores for each team
                    team_metrics = {}
                    for record in data:
                        team = record.get('TEAM', '')
                        if team:
                            if team not in team_metrics:
                                team_metrics[team] = {
                                    'total': sum(float(val) for val in record.values() if isinstance(val, (int, float))),
                                    'count': sum(1 for val in record.values() if isinstance(val, (int, float)))
                                }
                    
                    # Create visualization-friendly format
                    visualization_data = [
                        {
                            'name': team,
                            'value': metrics['total'] / metrics['count'] if metrics['count'] > 0 else 0
                        }
                        for team, metrics in team_metrics.items()
                    ]
                    
                    # Sort by value for better visualization
                    visualization_data.sort(key=lambda x: x['value'], reverse=True)
                
                self.logger.info(f"Successfully fetched dataset: {dataset_name}")

                # 1. Save data to local file system under sanitized tool_name directory
                sanitized_tool_name = self._sanitize_directory_name(self.tool_name)
                sanitized_dataset_name = self._sanitize_directory_name(dataset_name)
                
                tool_data_dir = os.path.join('data', sanitized_tool_name)
                local_file_path = os.path.join(tool_data_dir, f"{sanitized_dataset_name}.json")
                
                # Create tool-specific data directory if it doesn't exist
                os.makedirs(tool_data_dir, exist_ok=True)
                
                # Save the data
                with open(local_file_path, 'w') as f:
                    json.dump(data, f)

                # 2. Ingest the data into vector store using pipeline's ingest_data method
                dataset_loc = {
                    "location": local_file_path,
                    "type": "local_file"
                }
                metadata = {
                    "tool": sanitized_tool_name,
                    "dataset": sanitized_dataset_name,
                    "source_url": url,
                    "dataset_info": dataset_info
                }
                self.logger.info(f"[tools.py:GitHubTool] Calling ingest_data with parameters: dataset_nm={sanitized_dataset_name}, metadata={json.dumps(metadata, indent=2)}, location={json.dumps(dataset_loc, indent=2)}")
                ingest_result = self.rag_pipeline.ingest_data(
                    dataset_nm=sanitized_dataset_name,
                    metadata=metadata,
                    location=dataset_loc
                )

                if ingest_result.get('status') != 'success':
                    error_msg = ingest_result.get('error', 'Unknown error')
                    vector_store_details = ingest_result.get('vector_store_details', {})
                    self.logger.error(f"Failed to ingest data: {error_msg}")
                    self.logger.error(f"Vector store details: {json.dumps(vector_store_details, indent=2)}")
                    return {
                        'status': 'error',
                        'message': f"Failed to ingest data: {error_msg}",
                        'details': {
                            'ingest_result': ingest_result,
                            'vector_store_details': vector_store_details
                        }
                    }

                self.logger.info(f"Successfully ingested data: {json.dumps(ingest_result, indent=2)}")

                # 3. Process the user's query with vector store
                vector_db_query = self._get_vector_db_query(command)
                vector_store_results = self.rag_pipeline.process_query(vector_db_query)

                # 4. Format the final response using LLM
                final_prompt = f"""
                Please format the following information into a user-friendly response:
                Original Query: {command}
                Dataset: {dataset_name} from {dataset_info['url']}
                Vector Store Results: {json.dumps(vector_store_results, indent=2)}
                
                Include:
                1. A brief introduction about the dataset
                2. Key findings from the vector store search
                3. Relevant statistics or metrics
                4. Any limitations or caveats
                """
                formatted_response = self._format_final_response(final_prompt)
                
                # Update aggregation data to include visualization data
                aggregation_data = {
                    'vector_store': {
                        'results': vector_store_results,
                        'query': vector_db_query,
                        'dataset': sanitized_dataset_name
                    },
                    'raw_data': {
                        'sample': data[:3],
                        'total_records': len(data),
                        'schema': list(data[0].keys()) if data else []
                    }
                }

                if visualization_data:
                    aggregation_data['visualization'] = {
                        'type': 'chart',
                        'data': visualization_data,
                        'title': 'NFL Team Statistics',
                        'description': 'Average scores across different metrics for each NFL team'
                    }
                
                return {
                    'status': 'success',
                    'message': formatted_response,
                    'github_data': {
                        'url': url,
                        'dataset_name': sanitized_dataset_name,
                        'dataset_info': dataset_info
                    },
                    'aggregation_data': aggregation_data
                }
                
            except Exception as e:
                self.logger.error(f"Failed to process dataset: {str(e)}")
                return {
                    'status': 'error',
                    'message': f'Failed to process dataset: {str(e)}'
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

                    # 1. Save data to local file system under tool_nm directory
                    dataset_name = github_url.split('/')[-1].replace('.csv', '')
                    tool_data_dir = os.path.join('data', self.tool_name)
                    local_file_path = os.path.join(tool_data_dir, f"{dataset_name}.json")
                    
                    # Create tool-specific data directory if it doesn't exist
                    os.makedirs(tool_data_dir, exist_ok=True)
                    
                    # Save the data
                    with open(local_file_path, 'w') as f:
                        json.dump(data, f)

                    # 2. RAG pipeline is already initialized in __init__

                    # 3. Ingest the data into vector store using pipeline's ingest_data method
                    dataset_loc = {
                        "location": local_file_path,
                        "type": "local_file"
                    }
                    metadata = {
                        "tool": self.tool_name,
                        "dataset": dataset_name,
                        "source_url": github_url
                    }
                    self.logger.info(f"[tools.py:GitHubTool] Calling ingest_data with parameters: dataset_nm={dataset_name}, metadata={json.dumps(metadata, indent=2)}, location={json.dumps(dataset_loc, indent=2)}")
                    ingest_result = self.rag_pipeline.ingest_data(
                        dataset_nm=dataset_name,
                        metadata=metadata,
                        location=dataset_loc
                    )

                    # 4. Send update to LLM and get vector db query
                    llm_prompt = f"""
                    The data from GitHub has been stored in the vector store.
                    Dataset name: {dataset_name}
                    Please analyze the following user query and create a search query for the vector store:
                    {validation_json}
                    """
                    vector_db_query = self._get_vector_db_query(llm_prompt)

                    # 5. Process the query with vector store
                    vector_store_results = self.rag_pipeline.process_query(vector_db_query)

                    # 6. Format final response with LLM
                    final_prompt = f"""
                    Please format the following vector store results into a user-friendly response:
                    Original Query: {validation_json}
                    Vector Store Results: {json.dumps(vector_store_results)}
                    GitHub Data Source: {github_url}
                    """
                    formatted_response = self._format_final_response(final_prompt)
                    
                    return {
                        'status': 'success',
                        'github_data': {
                            'url': github_url,
                            'data': data,
                            'vector_store_results': vector_store_results,
                            'formatted_response': formatted_response
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

    def _get_vector_db_query(self, prompt: str) -> str:
        """
        Get vector db query from LLM using OpenAI.
        """
        try:
            openai = get_openai_client()
            
            system_prompt = """You are a helpful assistant that creates search queries for a vector database.
            Given a user's query and context about stored data, create a focused search query that will help retrieve relevant information.
            The query should be concise but include key terms and concepts that will match similar content in the vector store."""
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more focused queries
                max_tokens=100    # Limit response length as we need a concise query
            )
            
            # Extract the query from the response
            vector_query = response.choices[0].message.content.strip()
            self.logger.info(f"Generated vector DB query: {vector_query}")
            
            return vector_query
            
        except Exception as e:
            self.logger.error(f"Error generating vector DB query: {str(e)}")
            # Return a simplified version of the prompt if LLM fails
            return prompt.split('\n')[-1].strip()

    def _format_final_response(self, prompt: str) -> str:
        """
        Format the final response using OpenAI LLM.
        """
        try:
            openai = get_openai_client()
            
            system_prompt = """You are a helpful assistant that formats search results into clear, user-friendly responses.
            Given vector store results and the original query, create a well-structured response that:
            1. Directly answers the user's question
            2. Provides relevant supporting information from the vector store results
            3. Maintains a natural, conversational tone
            4. Includes specific data points when available
            5. Acknowledges any limitations or uncertainties in the data"""
            
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,  # Higher temperature for more natural responses
                max_tokens=500    # Allow longer responses for comprehensive answers
            )
            
            # Extract the formatted response
            formatted_response = response.choices[0].message.content.strip()
            self.logger.info("Generated formatted response")
            
            return formatted_response
            
        except Exception as e:
            self.logger.error(f"Error formatting final response: {str(e)}")
            # Return a basic response if LLM fails
            return f"Here are the search results: {prompt}"

def create_tool(tool_data: Dict[str, Any]) -> Tool:
    """Create a tool instance based on tool data."""
    tool_types = {
        "database": DatabaseTool,
        "apiservice": APITool,
        "webservice": WebServiceTool,
        "github": GitHubTool,
        "python": PythonTool,
        "react": ReactTool
    }
    
    tool_type = (tool_data.get("type") or tool_data.get("tool_type") or "").lower()
    if not tool_type:
        raise ValueError("Tool type not specified")
    
    # Try to match case-insensitive
    for known_type in tool_types:
        if known_type.lower() == tool_type.lower():
            tool_type = known_type
            break
    else:
        raise ValueError(f"Unknown tool type: {tool_type}")
    
    tool_class = tool_types[tool_type]
    
    # Common parameters for all tools
    common_params = {
        'tool_id': tool_data["id"],
        'tool_name': tool_data["tool_name"],
        'hostname': tool_data.get("hostname", ""),
        'username': tool_data.get("username", ""),
        'password': tool_data.get("password", ""),
        'auth_method': tool_data.get("auth_method", "None"),
        'description': tool_data.get("description", "")
    }
    
    # Additional parameters based on tool type
    if tool_type == 'github':
        return tool_class(
            **common_params,
            max_rows=tool_data.get('max_rows', 100)
        )
    elif tool_type == 'database':
        return tool_class(
            **common_params,
            database=tool_data['database'],
            port=tool_data.get('port', 3306)
        )
    elif tool_type == 'apiservice':
        return tool_class(
            **common_params,
            api_version=tool_data.get('api_version', 'v1'),
            timeout=tool_data.get('timeout', 30)
        )
    elif tool_type == 'webservice':
        return tool_class(
            **common_params,
            service_type=tool_data.get('service_type', 'REST'),
            timeout=tool_data.get('timeout', 30)
        )
    elif tool_type == 'python':
        return PythonTool(
            **common_params,
            python_version=tool_data.get('python_version', '3.8')
        )
    elif tool_type == 'react':
        return ReactTool(
            **common_params,
            react_version=tool_data.get('react_version', '18.0')
        )
    else:
        return tool_class(**common_params)