import unittest
import sys
import os
import logging

# Get the absolute path to the project root
project_root = os.path.abspath(os.path.dirname(__file__))
parent_dir = os.path.dirname(project_root)

# Add both the project root and parent directory to Python path
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.core.tools import GitHubTool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestGitHubTool(unittest.TestCase):
    def setUp(self):
        # Initialize GitHubTool with required parameters
        self.github_tool = GitHubTool(
            tool_id="test_github_tool",
            tool_name="GitHub Tool",
            hostname="github.com",
            username="test_user",
            password="test_password",
            auth_method="basic"
        )
        self.logger = logging.getLogger(__name__)

    def test_natural_language_nfl_extraction(self):
        """Test extracting NFL dataset from natural language response."""
        # Test message from OpenAI that doesn't contain direct URL
        openai_response = """I'm sorry, but as an AI with access to Github opensource datasets, I do not have direct access to data specifically pertaining to NFL Favorite Team. Github datasets mainly include repositories related to programming languages, user profiles, and programming projects. For NFL data, a sports-related database or sports API would be more appropriate. Unfortunately, I do not currently have access to these types of databases."""
        
        # Execute the GitHub tool with the response
        result = self.github_tool.execute(openai_response)
        
        # Print debug information
        print("\nTest Result:", result)
        
        # Verify the result
        self.assertEqual(result['status'], 'success', f"Failed to process NFL dataset. Error: {result.get('message', 'Unknown error')}")
        self.assertIn('github_data', result, "Response missing github_data field")
        self.assertIn('data', result['github_data'], "Response missing data field")
        self.assertIn('url', result['github_data'], "Response missing URL field")
        
        # Verify URL points to the correct dataset
        expected_url = "https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv"
        self.assertEqual(result['github_data']['url'], expected_url, "Incorrect dataset URL")
        
        # Verify data structure
        data = result['github_data']['data']
        self.assertIsInstance(data, list, "Data should be a list")
        self.assertTrue(len(data) > 0, "Data should not be empty")
        
        # Verify expected columns are present in the first row
        expected_columns = {'category', 'description'}
        first_row = data[0]
        self.assertTrue(all(col in first_row for col in expected_columns), 
                       f"Missing expected columns. Found: {set(first_row.keys())}")

    def test_dataset_name_extraction_methods(self):
        """Test different methods of dataset name extraction."""
        test_cases = [
            {
                'input': "Can you get the NFL Favorite Team dataset?",
                'expected_dataset': 'nfl-favorite-team',
                'method': 'pattern matching'
            },
            {
                'input': "I need data about NFL team preferences",
                'expected_dataset': 'nfl-favorite-team',
                'method': 'known mappings'
            },
            {
                'input': "Show me the football dataset information",
                'expected_dataset': 'nfl-favorite-team',
                'method': 'known mappings'
            }
        ]
        
        for case in test_cases:
            dataset_name = self.github_tool._extract_dataset_name_from_text(case['input'])
            self.assertEqual(
                dataset_name, 
                case['expected_dataset'],
                f"Failed to extract dataset name using {case['method']} from: {case['input']}"
            )

    def test_error_handling(self):
        """Test error handling for invalid inputs."""
        test_cases = [
            {
                'input': "Show me data about nonexistent dataset",
                'expected_status': 'error',
                'expected_message': 'No GitHub URL or dataset found in command'
            },
            {
                'input': "",
                'expected_status': 'error',
                'expected_message': 'No GitHub URL or dataset found in command'
            }
        ]
        
        for case in test_cases:
            result = self.github_tool.execute(case['input'])
            self.assertEqual(
                result['status'],
                case['expected_status'],
                f"Unexpected status for input: {case['input']}"
            )
            self.assertEqual(
                result['message'],
                case['expected_message'],
                f"Unexpected error message for input: {case['input']}"
            )

def test_fivethirtyeight_tool():
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
    
    # Test cases
    test_cases = [
        # Test with exact dataset name
        "Please get the nfl-favorite-team dataset from FiveThirtyEight data repository",
        
        # Test with partial dataset name
        "Can you fetch the NFL favorite team data from FiveThirtyEight?",
        
        # Test with dataset name and 'data' keyword
        "I need the NFL team data from the FiveThirtyEight repository",
        
        # Test with 'get' command format
        "get nfl-favorite-team dataset from FiveThirtyEight",
        
        # Test with direct URL in markdown
        """Get the data from [https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv](https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv)""",
        
        # Test with raw URL
        "The data is at https://raw.githubusercontent.com/fivethirtyeight/data/refs/heads/master/nfl-favorite-team/team-picking-categories.csv",
        
        # Test with GitHub blob URL
        "Find it here: https://github.com/fivethirtyeight/data/blob/master/nfl-favorite-team/team-picking-categories.csv",
        
        # Test with GitHub tree URL
        "Check out https://github.com/fivethirtyeight/data/tree/master/nfl-favorite-team"
    ]
    
    for i, test_input in enumerate(test_cases, 1):
        logger.info(f"\nTest Case {i}:")
        logger.info(f"Input: {test_input}")
        
        # Test URL extraction
        url = tool._extract_github_url(test_input)
        logger.info(f"Extracted URL: {url}")
        
        if url:
            # Test tool execution
            result = tool.execute(test_input)
            logger.info("Execution result:")
            if result.get('status') == 'success':
                data = result.get('github_data', {}).get('data', [])
                if data:
                    logger.info(f"Successfully retrieved data with {len(data)} rows")
                    logger.info("First row of data:")
                    logger.info(data[0])
            else:
                logger.warning(f"Execution failed: {result.get('message')}")
        else:
            logger.warning("No URL extracted")
        
        logger.info("-" * 80)

if __name__ == '__main__':
    print("\nRunning tests from:", os.path.abspath(__file__))
    print("Python path:", sys.path)
    unittest.main(verbosity=2) 