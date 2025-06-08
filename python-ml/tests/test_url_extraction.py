from app.core.tools import GitHubTool
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

def test_url_extraction():
    # Create a GitHub tool instance
    github_tool = GitHubTool(
        tool_id=1,
        tool_name="Test GitHub Tool",
        hostname="github.com",
        username="test",
        password="test",
        auth_method="none",
        description="Test tool"
    )
    
    # Test input with markdown-formatted URL
    test_input = """To retrieve the Avocado Prices, I will fetch the data from the respective Github URL provided in the tools. The URL for Avocado Prices is: [https://raw.githubusercontent.com/fivethirtyeight/data/master/avocado-prices/avocado.csv](https://raw.githubusercontent.com/fivethirtyeight/data/master/avocado-prices/avocado.csv)"""
    
    # Extract URL
    extracted_url = github_tool._extract_github_url(test_input)
    print("\nTest Results:")
    print(f"Extracted URL: {extracted_url}")
    
    # Execute the tool with the test input
    result = github_tool.execute(test_input)
    print("\nTool Execution Result:")
    print(f"Status: {result.get('status')}")
    print(f"Message: {result.get('message')}")
    if 'github_data' in result:
        print("GitHub data successfully retrieved!")

if __name__ == "__main__":
    test_url_extraction() 