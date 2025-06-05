from typing import Dict, Any, List, Type
from app.core.tools import Tool, DatabaseTool, APITool, WebServiceTool, GitHubTool
from app.utils.logger import logger

class ToolService:
    """Service for managing tool operations"""
    
    def __init__(self):
        self.tools: Dict[int, Tool] = {}
        self.tool_types: Dict[str, Type[Tool]] = {
            'database': DatabaseTool,
            'api': APITool,
            'webservice': WebServiceTool,
            'github': GitHubTool
        }

    def create_tool(self, tool_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new tool"""
        try:
            tool_type = tool_data.get('type', '').lower()
            if tool_type not in self.tool_types:
                raise ValueError(f"Invalid tool type: {tool_type}")

            tool_class = self.tool_types[tool_type]
            
            # Common parameters for all tools
            common_params = {
                'tool_id': tool_data['tool_id'],
                'tool_name': tool_data['name'],
                'hostname': tool_data['hostname'],
                'username': tool_data.get('username', ''),
                'password': tool_data.get('password', ''),
                'auth_method': tool_data.get('auth_method', 'none'),
                'description': tool_data.get('description', '')
            }
            
            # Additional parameters based on tool type
            if tool_type == 'database':
                tool = tool_class(
                    **common_params,
                    database=tool_data['database'],
                    port=tool_data.get('port', 3306)
                )
            elif tool_type == 'api':
                tool = tool_class(
                    **common_params,
                    api_version=tool_data.get('api_version', 'v1'),
                    timeout=tool_data.get('timeout', 30)
                )
            elif tool_type == 'webservice':
                tool = tool_class(
                    **common_params,
                    service_type=tool_data.get('service_type', 'REST'),
                    timeout=tool_data.get('timeout', 30)
                )
            elif tool_type == 'github':
                tool = tool_class(
                    **common_params,
                    max_rows=tool_data.get('max_rows', 100)
                )
            
            self.tools[tool.tool_id] = tool
            logger.info(f"Tool {tool.tool_id} ({tool_type}) created successfully")
            
            return self.get_tool_info(tool)
        except Exception as e:
            logger.error(f"Failed to create tool: {str(e)}")
            raise

    def get_tool(self, tool_id: int) -> Tool:
        """Get a tool by ID"""
        tool = self.tools.get(tool_id)
        if not tool:
            raise ValueError(f"Tool {tool_id} not found")
        return tool

    def get_tool_info(self, tool: Tool) -> Dict[str, Any]:
        """Get tool information in dictionary format"""
        info = {
            'tool_id': tool.tool_id,
            'name': tool.tool_name,
            'type': tool.__class__.__name__,
            'hostname': tool.hostname,
            'auth_method': tool.auth_method,
            'description': tool.description,
            'is_connected': tool.is_connected
        }
        
        # Add tool-specific information
        if isinstance(tool, DatabaseTool):
            info.update({
                'database': tool.database,
                'port': tool.port
            })
        elif isinstance(tool, APITool):
            info.update({
                'api_version': tool.api_version,
                'timeout': tool.timeout
            })
        elif isinstance(tool, WebServiceTool):
            info.update({
                'service_type': tool.service_type,
                'timeout': tool.timeout
            })
        elif isinstance(tool, GitHubTool):
            info.update({
                'max_rows': tool.max_rows
            })
            
        return info

    def execute_tool(self, tool_id: int, command: str) -> Dict[str, Any]:
        """Execute a command using a specific tool"""
        try:
            tool = self.get_tool(tool_id)
            logger.info(f"Executing command with tool {tool_id}")
            return tool.execute(command)
        except Exception as e:
            logger.error(f"Failed to execute tool {tool_id}: {str(e)}")
            raise

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [self.get_tool_info(tool) for tool in self.tools.values()]

    def delete_tool(self, tool_id: int) -> None:
        """Delete a tool"""
        if tool_id not in self.tools:
            raise ValueError(f"Tool {tool_id} not found")
        del self.tools[tool_id] 