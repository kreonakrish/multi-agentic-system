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

    @property
    def is_connected(self) -> bool:
        """Check if tool is connected"""
        return self._is_connected

    def connect(self) -> bool:
        """Establish connection to the tool"""
        try:
            logger.info(f"Connecting to {self.tool_name}")
            # Implement actual connection logic in subclasses
            self._is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.tool_name}: {str(e)}")
            self._is_connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from the tool"""
        try:
            logger.info(f"Disconnecting from {self.tool_name}")
            self._is_connected = False
        except Exception as e:
            logger.error(f"Error disconnecting from {self.tool_name}: {str(e)}")

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
            "message": f"Tool {self.tool_name} ({self.__class__.__name__}) executed successfully"
        }

    @abstractmethod
    def execute(self, command: str) -> Dict[str, Any]:
        """Execute a command using the tool"""
        pass

class DatabaseTool(Tool):
    """Tool for database operations"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 database: str, port: Optional[int] = None,
                 description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.database = database
        self.port = port or 3306

    def execute(self, command: str) -> Dict[str, Any]:
        """Execute a database command"""
        try:
            if not self.is_connected and not self.connect():
                raise Exception("Failed to connect to database")

            logger.info(f"Executing database command on {self.database}")
            response = self.get_default_response(command)
            response.update({
                "database_specific": {
                    "database": self.database,
                    "port": self.port,
                    "query_type": self._get_query_type(command),
                    "affected_rows": 0  # Replace with actual count in implementation
                }
            })
            return response
        except Exception as e:
            logger.error(f"Database execution error: {str(e)}")
            raise

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

    def execute(self, command: str) -> Dict[str, Any]:
        """Execute an API command"""
        try:
            logger.info(f"Executing API command on {self.hostname}")
            response = self.get_default_response(command)
            response.update({
                "api_specific": {
                    "endpoint": f"{self.hostname}/api/{self.api_version}",
                    "timeout": self.timeout,
                    "method": self._get_http_method(command)
                }
            })
            return response
        except Exception as e:
            logger.error(f"API execution error: {str(e)}")
            raise

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

    def execute(self, command: str) -> Dict[str, Any]:
        """Execute a web service command"""
        try:
            logger.info(f"Executing web service command on {self.hostname}")
            response = self.get_default_response(command)
            response.update({
                "service_specific": {
                    "service_endpoint": f"{self.hostname}/service",
                    "service_type": self.service_type,
                    "timeout": self.timeout
                }
            })
            return response
        except Exception as e:
            logger.error(f"Web service execution error: {str(e)}")
            raise

class GitHubTool(Tool):
    """Tool for GitHub data operations"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str,
                 max_rows: int = 100, description: str = ""):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method, description)
        self.max_rows = max_rows
        self.logger = logging.getLogger(f'multi_agent_system.github_tool.{tool_id}')
        self.fivethirtyeight_index_url = "https://raw.githubusercontent.com/fivethirtyeight/data/master/index.csv"
        self.fivethirtyeight_base_url = "https://raw.githubusercontent.com/fivethirtyeight/data/master/"
        
        # Configure logging format to include timing
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s')
        for handler in self.logger.handlers:
            handler.setFormatter(formatter)

    def _load_fivethirtyeight_index(self) -> List[Dict[str, str]]:
        """Load the FiveThirtyEight dataset index file."""
        import time
        start_time = time.time()
        self.logger.info("Starting to load FiveThirtyEight index...")
        
        try:
            self.logger.debug(f"Fetching index from URL: {self.fivethirtyeight_index_url}")
            response = requests.get(self.fivethirtyeight_index_url)
            response.raise_for_status()
            
            # Log response details
            self.logger.debug(f"Response status: {response.status_code}")
            self.logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Parse CSV data
            df = pd.read_csv(StringIO(response.text))
            elapsed_time = time.time() - start_time
            self.logger.info(f"Successfully loaded index with {len(df)} datasets in {elapsed_time:.2f} seconds")
            
            # Convert to list of dictionaries
            return df.to_dict('records')
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error loading FiveThirtyEight index: {str(e)}")
            return []
        except pd.errors.EmptyDataError:
            self.logger.error("Index file is empty")
            return []
        except Exception as e:
            self.logger.error(f"Error loading FiveThirtyEight index: {str(e)}")
            return []

    def _find_dataset_by_name(self, dataset_name: str) -> Optional[Dict[str, str]]:
        """Find a dataset in the FiveThirtyEight index by name."""
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting dataset search for: {dataset_name}")
            index = self._load_fivethirtyeight_index()
            
            if not index:
                self.logger.error("Failed to load index, cannot proceed with search")
                return None
            
            # Clean up the dataset name
            clean_name = dataset_name.lower().strip()
            self.logger.debug(f"Cleaned dataset name: {clean_name}")
            
            # First try exact match
            self.logger.debug("Attempting exact match...")
            for dataset in index:
                if dataset['subfolder_name'].lower() == clean_name:
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Found exact match for {clean_name} in {elapsed_time:.2f} seconds")
                    self.logger.debug(f"Dataset details: {dataset}")
                    return dataset
            
            # Then try partial match
            self.logger.debug("No exact match found, trying partial matches...")
            matches = [
                dataset for dataset in index 
                if clean_name in dataset['subfolder_name'].lower()
            ]
            
            if matches:
                if len(matches) > 1:
                    self.logger.info(f"Found {len(matches)} matches for {clean_name}, using first match")
                    self.logger.debug(f"All matches: {[m['subfolder_name'] for m in matches]}")
                dataset = matches[0]
                elapsed_time = time.time() - start_time
                self.logger.info(f"Selected partial match {dataset['subfolder_name']} in {elapsed_time:.2f} seconds")
                return dataset
            
            elapsed_time = time.time() - start_time
            self.logger.warning(f"No dataset found matching name: {clean_name} (search took {elapsed_time:.2f} seconds)")
            return None
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Error finding dataset: {str(e)} (after {elapsed_time:.2f} seconds)")
            return None

    def _construct_dataset_url(self, dataset_info: Dict[str, str]) -> Optional[str]:
        """Construct the raw GitHub URL for a dataset."""
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting URL construction for dataset: {dataset_info.get('subfolder_name', 'unknown')}")
            
            # For NFL favorite team dataset, we know the exact URL
            if dataset_info['subfolder_name'] == 'nfl-favorite-team':
                url = "https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv"
                elapsed_time = time.time() - start_time
                self.logger.info(f"Using known URL for NFL dataset: {url} (took {elapsed_time:.2f} seconds)")
                return url

            # Use the dataset_url from the index
            if 'dataset_url' in dataset_info:
                # Convert GitHub web URL to raw URL
                url = dataset_info['dataset_url'].replace('github.com', 'raw.githubusercontent.com')
                url = url.replace('/blob/', '/')
                
                elapsed_time = time.time() - start_time
                self.logger.info(f"Using index URL for dataset: {url} (took {elapsed_time:.2f} seconds)")
                return url
            
            elapsed_time = time.time() - start_time
            self.logger.warning(f"No URL found for dataset: {dataset_info.get('subfolder_name')} (took {elapsed_time:.2f} seconds)")
            return None
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Error constructing dataset URL: {str(e)} (after {elapsed_time:.2f} seconds)")
            return None

    def _extract_dataset_name_from_text(self, text: str) -> Optional[str]:
        """Extract dataset name from natural language text using NLP techniques."""
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"[DATASET EXTRACTION] Starting dataset name extraction from text: {text[:100]}...")
            
            # First try known dataset mappings
            known_mappings = {
                'nfl': 'nfl-favorite-team',
                'football': 'nfl-favorite-team',
                'favorite team': 'nfl-favorite-team',
                'team preference': 'nfl-favorite-team',
                'nfl favorite': 'nfl-favorite-team',
                'nfl favorite team': 'nfl-favorite-team',
                'nfl team': 'nfl-favorite-team',
                'nfl teams': 'nfl-favorite-team',
                'favorite nfl': 'nfl-favorite-team',
                'favorite nfl team': 'nfl-favorite-team',
                'nfl data': 'nfl-favorite-team',
                'football team': 'nfl-favorite-team',
                'football teams': 'nfl-favorite-team',
                'avocado': 'avocado-prices',
                'avocado prices': 'avocado-prices',
                'comic': 'comic-characters',
                'comic characters': 'comic-characters',
                'air quality': 'air-quality',
                'co2': 'co2-emissions',
                'covid': 'covid-19-data',
                'covid19': 'covid-19-data',
                'covid-19': 'covid-19-data',
                'countries': 'country-list',
                'country list': 'country-list',
                'currency': 'currency-codes',
                'currency codes': 'currency-codes',
                'iris': 'iris-dataset'
            }
            
            # Try to match known datasets
            text_lower = text.lower()
            self.logger.debug(f"[DATASET EXTRACTION] Looking for matches in text: '{text_lower}'")
            
            for key, dataset in known_mappings.items():
                self.logger.debug(f"[DATASET EXTRACTION] Checking if '{key}' is in '{text_lower}'")
                if key in text_lower:
                    self.logger.info(f"[DATASET EXTRACTION] Found exact match for dataset: {dataset}")
                    return dataset  # Early return after finding a match
            
            self.logger.debug("[DATASET EXTRACTION] No matches found in known mappings")
            
            # If no exact match, try to load the index file
            dataset_found = False
            try:
                self.logger.debug("[DATASET EXTRACTION] Loading FiveThirtyEight index...")
                index_response = requests.get(self.fivethirtyeight_index_url)
                index_response.raise_for_status()
                
                # Parse CSV content
                index_df = pd.read_csv(StringIO(index_response.text))
                self.logger.info(f"[DATASET EXTRACTION] Loaded {len(index_df)} datasets from index")
                
                # Search for dataset in index
                for _, row in index_df.iterrows():
                    dataset_name = row['subfolder_name'].lower()
                    if any(keyword in dataset_name for keyword in text_lower.split()):
                        self.logger.info(f"[DATASET EXTRACTION] Found matching dataset in index: {row['subfolder_name']}")
                        dataset_found = True
                        return row['subfolder_name']
                
            except Exception as e:
                self.logger.error(f"[DATASET EXTRACTION] Error loading index file: {str(e)}", exc_info=True)
            
            # Only try NLP-based matching if index search failed
            if not dataset_found:
                try:
                    # Download required NLTK data if not already downloaded
                    try:
                        nltk.download('punkt', quiet=True)
                        nltk.download('stopwords', quiet=True)
                        nltk.download('wordnet', quiet=True)
                        nltk.download('averaged_perceptron_tagger', quiet=True)
                    except Exception as e:
                        self.logger.warning(f"[DATASET EXTRACTION] Error downloading NLTK data: {str(e)}")
                    
                    # Use simple tokenization first
                    tokens = text_lower.split()
                    
                    # If NLTK is available, use it for better tokenization
                    try:
                        from nltk.tokenize import TreebankWordTokenizer
                        tokenizer = TreebankWordTokenizer()
                        tokens = tokenizer.tokenize(text_lower)
                    except Exception as e:
                        self.logger.warning(f"[DATASET EXTRACTION] Falling back to simple tokenization: {str(e)}")
                    
                    stop_words = set(stopwords.words('english'))
                    lemmatizer = WordNetLemmatizer()
                    
                    # Extract key terms
                    key_terms = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]
                    self.logger.debug(f"[DATASET EXTRACTION] Extracted key terms: {key_terms}")
                    
                    # Try to match key terms with known datasets
                    for term in key_terms:
                        for key, dataset in known_mappings.items():
                            if term in key.split():
                                self.logger.info(f"[DATASET EXTRACTION] Found NLP match for dataset: {dataset}")
                                return dataset
                
                except Exception as e:
                    self.logger.error(f"[DATASET EXTRACTION] Error in NLP processing: {str(e)}", exc_info=True)
                
                self.logger.warning("[DATASET EXTRACTION] Could not find matching dataset")
                return None
            
        except Exception as e:
            self.logger.error(f"[DATASET EXTRACTION] Error extracting dataset name: {str(e)}", exc_info=True)
            return None
        finally:
            end_time = time.time()
            self.logger.debug(f"[DATASET EXTRACTION] Extraction took {end_time - start_time:.2f} seconds")

    def execute(self, command: str) -> Dict[str, Any]:
        """Execute the GitHub tool command."""
        import time
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting GitHub tool execution with command: {command}")
            
            # Check if this is a dataset request
            dataset_keywords = ['data', 'dataset', 'stats', 'statistics', 'information']
            is_dataset_request = any(keyword in command.lower() for keyword in dataset_keywords)
            
            if not is_dataset_request:
                self.logger.debug("Command does not appear to be a dataset request")
                return {
                    'status': 'error',
                    'message': 'Command does not appear to be requesting a dataset'
                }
            
            # First try to extract dataset name from the command
            self.logger.debug("Attempting to extract dataset name from command...")
            dataset_name = self._extract_dataset_name_from_text(command)
            if not dataset_name:
                elapsed_time = time.time() - start_time
                self.logger.warning(f"No dataset name found in command (took {elapsed_time:.2f} seconds)")
                return {
                    'status': 'error',
                    'message': 'No dataset name could be extracted from the command'
                }
            
            # Look up dataset in FiveThirtyEight index
            self.logger.debug(f"Looking up dataset: {dataset_name}")
            dataset_info = self._find_dataset_by_name(dataset_name)
            if not dataset_info:
                elapsed_time = time.time() - start_time
                self.logger.warning(f"Dataset not found: {dataset_name} (took {elapsed_time:.2f} seconds)")
                return {
                    'status': 'error',
                    'message': f'Dataset not found: {dataset_name}'
                }
            
            # Construct URL for the dataset
            self.logger.debug(f"Constructing URL for dataset: {dataset_name}")
            url = self._construct_dataset_url(dataset_info)
            if not url:
                elapsed_time = time.time() - start_time
                self.logger.warning(f"Could not construct URL for dataset: {dataset_name} (took {elapsed_time:.2f} seconds)")
                return {
                    'status': 'error',
                    'message': f'Could not construct URL for dataset: {dataset_name}'
                }
            
            # Download and process the data
            self.logger.debug(f"Downloading dataset from URL: {url}")
            try:
                response = requests.get(url)
                response.raise_for_status()
                
                # Log response details
                self.logger.debug(f"Response status: {response.status_code}")
                self.logger.debug(f"Response headers: {dict(response.headers)}")
                
                # Parse CSV data
                import pandas as pd
                from io import StringIO
                import json
                
                df = pd.read_csv(StringIO(response.text))
                self.logger.debug(f"Successfully parsed CSV with {len(df)} rows and {len(df.columns)} columns")
                
                # Convert DataFrame to list of dictionaries
                data = df.to_dict('records')
                
                # Limit the number of rows if specified
                if self.max_rows and len(data) > self.max_rows:
                    self.logger.debug(f"Limiting output to {self.max_rows} rows")
                    data = data[:self.max_rows]
                
                elapsed_time = time.time() - start_time
                self.logger.info(f"Successfully fetched dataset: {dataset_name} (took {elapsed_time:.2f} seconds)")

                # Create a user-friendly summary of the data
                summary = f"\nI've found and retrieved the {dataset_name} dataset from FiveThirtyEight. Here's what I found:\n\n"
                summary += f"Dataset: {dataset_info['subfolder_name']}\n"
                summary += f"Source: {dataset_info['dataset_url']}\n"
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
                
                # Create a formatted table of the first few rows
                table = df.head().to_string()
                
                # Convert data to JSON string for detailed view
                json_data = "\n\nDetailed JSON data:\n```json\n"
                json_data += json.dumps(data[:3], indent=2)  # Show first 3 records
                json_data += "\n```"
                
                return {
                    'status': 'success',
                    'message': summary + table + json_data,
                    'data': data,  # Include raw data directly in response
                    'github_data': {
                        'url': url,
                        'data': data,
                        'dataset_name': dataset_name,
                        'dataset_info': dataset_info
                    }
                }
                
            except requests.exceptions.RequestException as e:
                elapsed_time = time.time() - start_time
                self.logger.error(f"Network error downloading dataset: {str(e)} (after {elapsed_time:.2f} seconds)")
                return {
                    'status': 'error',
                    'message': f'Failed to download dataset: Network error - {str(e)}'
                }
            except pd.errors.EmptyDataError:
                elapsed_time = time.time() - start_time
                self.logger.error(f"Dataset file is empty (after {elapsed_time:.2f} seconds)")
                return {
                    'status': 'error',
                    'message': 'Dataset file is empty'
                }
            except Exception as e:
                elapsed_time = time.time() - start_time
                self.logger.error(f"Error processing dataset: {str(e)} (after {elapsed_time:.2f} seconds)")
                return {
                    'status': 'error',
                    'message': f'Failed to process dataset: {str(e)}'
                }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Error executing GitHub command: {str(e)} (after {elapsed_time:.2f} seconds)")
            return {
                'status': 'error',
                'message': f'Error executing GitHub command: {str(e)}'
            }

    def validate_response(self, validation_json: str) -> Dict[str, Any]:
        """Validate and process the response from LLM."""
        import time
        start_time = time.time()
        
        try:
            self.logger.info("Starting response validation...")
            
            # Check if LLM response has a GitHub CSV raw URL
            pattern = r'https://raw\.githubusercontent\.com/[^\s\'"]+'
            self.logger.debug(f"Searching for GitHub raw URL pattern: {pattern}")
            match = re.search(pattern, validation_json)
            
            if match:
                github_url = match.group(0)
                self.logger.info(f"Found GitHub URL: {github_url}")
                
                # Try to download and process the data
                self.logger.debug("Attempting to download and process data...")
                try:
                    response = requests.get(github_url)
                    response.raise_for_status()
                    
                    # Log response details
                    self.logger.debug(f"Response status: {response.status_code}")
                    self.logger.debug(f"Response headers: {dict(response.headers)}")
                    
                    # Parse CSV data
                    import pandas as pd
                    from io import StringIO
                    
                    df = pd.read_csv(StringIO(response.text))
                    self.logger.debug(f"Successfully parsed CSV with {len(df)} rows and {len(df.columns)} columns")
                    
                    # Convert DataFrame to list of dictionaries
                    data = df.to_dict('records')
                    
                    # Limit the number of rows if specified
                    if self.max_rows and len(data) > self.max_rows:
                        self.logger.debug(f"Limiting output to {self.max_rows} rows")
                        data = data[:self.max_rows]
                    
                    elapsed_time = time.time() - start_time
                    self.logger.info(f"Successfully validated and processed GitHub URL (took {elapsed_time:.2f} seconds)")
                    return {
                        'status': 'success',
                        'github_data': {
                            'url': github_url,
                            'data': data
                        }
                    }
                    
                except requests.exceptions.RequestException as e:
                    elapsed_time = time.time() - start_time
                    self.logger.error(f"Network error downloading GitHub data: {str(e)} (after {elapsed_time:.2f} seconds)")
                    return {
                        'status': 'error',
                        'message': f'Failed to download GitHub data: Network error - {str(e)}'
                    }
                except pd.errors.EmptyDataError:
                    elapsed_time = time.time() - start_time
                    self.logger.error(f"Dataset file is empty (after {elapsed_time:.2f} seconds)")
                    return {
                        'status': 'error',
                        'message': 'Dataset file is empty'
                    }
                except Exception as e:
                    elapsed_time = time.time() - start_time
                    self.logger.error(f"Error processing GitHub data: {str(e)} (after {elapsed_time:.2f} seconds)")
                    return {
                        'status': 'error',
                        'message': f'Failed to process GitHub data: {str(e)}'
                    }
            
            # If no direct URL found, try to extract dataset name
            self.logger.debug("No direct URL found, attempting to extract dataset name...")
            dataset_name = self._extract_dataset_name_from_text(validation_json)
            if dataset_name:
                self.logger.info(f"Found dataset name: {dataset_name}")
                # Look up dataset in index
                self.logger.debug(f"Looking up dataset in index: {dataset_name}")
                dataset_info = self._find_dataset_by_name(dataset_name)
                if dataset_info:
                    self.logger.debug(f"Found dataset info: {dataset_info}")
                    url = self._construct_dataset_url(dataset_info)
                    if url:
                        # Download and process the data
                        self.logger.debug(f"Attempting to download dataset from URL: {url}")
                        try:
                            response = requests.get(url)
                            response.raise_for_status()
                            
                            # Log response details
                            self.logger.debug(f"Response status: {response.status_code}")
                            self.logger.debug(f"Response headers: {dict(response.headers)}")
                            
                            # Parse CSV data
                            import pandas as pd
                            from io import StringIO
                            
                            df = pd.read_csv(StringIO(response.text))
                            self.logger.debug(f"Successfully parsed CSV with {len(df)} rows and {len(df.columns)} columns")
                            
                            # Convert DataFrame to list of dictionaries
                            data = df.to_dict('records')
                            
                            # Limit the number of rows if specified
                            if self.max_rows and len(data) > self.max_rows:
                                self.logger.debug(f"Limiting output to {self.max_rows} rows")
                                data = data[:self.max_rows]
                            
                            elapsed_time = time.time() - start_time
                            self.logger.info(f"Successfully validated and processed dataset: {dataset_name} (took {elapsed_time:.2f} seconds)")
                            
                            # Create a summary with JSON data
                            summary = f"Here's the data from the {dataset_name} dataset:\n\n```json\n"
                            summary += json.dumps(data[:3], indent=2)  # Show first 3 records
                            summary += "\n```"
                            
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
                            
                        except requests.exceptions.RequestException as e:
                            elapsed_time = time.time() - start_time
                            self.logger.error(f"Network error downloading dataset: {str(e)} (after {elapsed_time:.2f} seconds)")
                            return {
                                'status': 'error',
                                'message': f'Failed to download dataset: Network error - {str(e)}'
                            }
                        except pd.errors.EmptyDataError:
                            elapsed_time = time.time() - start_time
                            self.logger.error(f"Dataset file is empty (after {elapsed_time:.2f} seconds)")
                            return {
                                'status': 'error',
                                'message': 'Dataset file is empty'
                            }
                        except Exception as e:
                            elapsed_time = time.time() - start_time
                            self.logger.error(f"Error processing dataset: {str(e)} (after {elapsed_time:.2f} seconds)")
                            return {
                                'status': 'error',
                                'message': f'Failed to process dataset: {str(e)}'
                            }
                    else:
                        elapsed_time = time.time() - start_time
                        self.logger.warning(f"Could not construct URL for dataset: {dataset_name} (took {elapsed_time:.2f} seconds)")
                else:
                    elapsed_time = time.time() - start_time
                    self.logger.warning(f"Dataset info not found for: {dataset_name} (took {elapsed_time:.2f} seconds)")
            else:
                elapsed_time = time.time() - start_time
                self.logger.warning(f"No dataset name could be extracted (took {elapsed_time:.2f} seconds)")
            
            elapsed_time = time.time() - start_time
            self.logger.warning(f"No GitHub URL or dataset found in response (took {elapsed_time:.2f} seconds)")
            return {
                'status': 'error',
                'message': 'No GitHub URL or dataset found in response'
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"Error validating response: {str(e)} (after {elapsed_time:.2f} seconds)")
            return {
                'status': 'error',
                'message': f'Error validating response: {str(e)}'
            }

def create_tool(tool_data: Dict[str, Any]) -> Tool:
    """Create a tool instance based on tool data."""
    tool_types = {
        "database": DatabaseTool,
        "apiservice": APITool,
        "webservice": WebServiceTool,
        "github": GitHubTool
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
    else:
        return tool_class(**common_params)