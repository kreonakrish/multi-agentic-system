from typing import Dict, Any, List, Type
from app.core.tools import Tool, DatabaseTool, APITool, WebServiceTool, GitHubTool, create_tool
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
            # Create tool instance using the factory function
            tool = create_tool(tool_data)
            
            # Store the tool
            self.tools[tool.tool_id] = tool
            logger.info(f"Tool {tool.tool_id} ({tool.__class__.__name__}) created successfully")
            
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