from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.utils.logger import logger

class Tool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, tool_id: int, tool_name: str, hostname: str,
                 username: str, password: str, auth_method: str):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.hostname = hostname
        self.username = username
        self._password = password  # Note the protected attribute
        self.auth_method = auth_method
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
                 database: str, port: Optional[int] = None):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method)
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
                 api_version: str = 'v1', timeout: int = 30):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method)
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
                 service_type: str = 'REST', timeout: int = 30):
        super().__init__(tool_id, tool_name, hostname, username, password, auth_method)
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