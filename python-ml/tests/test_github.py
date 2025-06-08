import sys
import os
import logging

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.tools import GitHubTool

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_github_tool():
    # Create a GitHub tool instance
    tool = GitHubTool(
        tool_id=1,
        tool_name="Test GitHub Tool",
        hostname="github.com",
        username="test",
        password="test",
        auth_method="none",
        description="Test tool"
    )
    
    # Test with NFL favorite team dataset
    test_input = "Please get the nfl-favorite-team dataset from FiveThirtyEight data repository"
    
    # Test tool execution
    logger.info("Testing tool execution...")
    result = tool.execute(test_input)
    logger.info(f"Execution result: {result}")
    
    # Verify the result
    assert result['status'] == 'success', "Tool execution should succeed"
    assert 'github_data' in result, "Result should contain github_data"
    assert 'url' in result['github_data'], "Result should contain URL"
    assert 'data' in result['github_data'], "Result should contain data"
    assert len(result['github_data']['data']) > 0, "Data should not be empty"
    
    # Test with invalid dataset
    test_input = "Please get the nonexistent-dataset from FiveThirtyEight"
    result = tool.execute(test_input)
    assert result['status'] == 'error', "Tool should fail for nonexistent dataset"

if __name__ == "__main__":
    test_github_tool() 