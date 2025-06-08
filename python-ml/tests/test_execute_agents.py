import unittest
import requests
import json
import logging
import time
from datetime import datetime
from app.utils.db import get_db_connection, safe_close_connection, DB_CONFIG

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TestAgentExecutor(unittest.TestCase):
    def setUp(self):
        """Set up test case - create a team and agents in the database first"""
        start_time = time.time()
        logger.info("Starting test setup...")
        
        self.base_url = "http://localhost:5000"
        
        # Create team and agents in database
        try:
            db_start_time = time.time()
            self.conn = get_db_connection()
            self.cursor = self.conn.cursor()
            logger.info(f"Database connection established in {time.time() - db_start_time:.2f} seconds")
            
            # Create team
            team_start_time = time.time()
            self.cursor.execute("""
                INSERT INTO teams (name)
                VALUES (%s)
            """, ("Test Team",))
            self.conn.commit()
            self.team_id = self.cursor.lastrowid
            logger.info(f"Created test team with ID: {self.team_id} in {time.time() - team_start_time:.2f} seconds")
            
            # Create sender agent
            agent_start_time = time.time()
            self.cursor.execute("""
                INSERT INTO agents (name, memory_type, foundation_model, status)
                VALUES (%s, %s, %s, %s)
            """, ("Sender Agent", "SHORT_TERM_MEMORY", "gpt-4", "inactive"))
            self.conn.commit()
            self.sender_id = self.cursor.lastrowid
            logger.info(f"Created sender agent with ID: {self.sender_id} in {time.time() - agent_start_time:.2f} seconds")
            
            # Create receiver agent
            receiver_start_time = time.time()
            self.cursor.execute("""
                INSERT INTO agents (name, memory_type, foundation_model, status)
                VALUES (%s, %s, %s, %s)
            """, ("Receiver Agent", "SHORT_TERM_MEMORY", "gpt-4", "inactive"))
            self.conn.commit()
            self.receiver_id = self.cursor.lastrowid
            logger.info(f"Created receiver agent with ID: {self.receiver_id} in {time.time() - receiver_start_time:.2f} seconds")
            
            # Create DBX tool
            tool_start_time = time.time()
            self.cursor.execute("""
                INSERT INTO tools (tool_name, tool_type, hostname, auth_method)
                VALUES (%s, %s, %s, %s)
            """, ("DBX Tool", "WebService", "databricks.example.com", "token"))
            self.conn.commit()
            self.tool_id = self.cursor.lastrowid
            logger.info(f"Created DBX tool with ID: {self.tool_id} in {time.time() - tool_start_time:.2f} seconds")
            
            # Associate agents with team
            assoc_start_time = time.time()
            self.cursor.execute("""
                INSERT INTO team_agents (team_id, agent_id)
                VALUES (%s, %s), (%s, %s)
            """, (self.team_id, self.sender_id, self.team_id, self.receiver_id))
            self.conn.commit()
            logger.info(f"Associated agents with team {self.team_id} in {time.time() - assoc_start_time:.2f} seconds")
            
            # Associate tool with team
            tool_assoc_start_time = time.time()
            self.cursor.execute("""
                INSERT INTO team_tool_permissions (team_id, tool_id, permission_level)
                VALUES (%s, %s, %s)
            """, (self.team_id, self.tool_id, "write"))
            self.conn.commit()
            logger.info(f"Associated tool {self.tool_id} with team {self.team_id} in {time.time() - tool_assoc_start_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in test setup: {str(e)}")
            if hasattr(self, 'conn'):
                safe_close_connection(self.conn, self.cursor)
            raise
            
        logger.info(f"Total setup time: {time.time() - start_time:.2f} seconds")
    
    def tearDown(self):
        """Clean up after test - delete the agents, team, and tool"""
        start_time = time.time()
        logger.info("Starting test cleanup...")
        
        try:
            if not hasattr(self, 'conn') or not self.conn.is_connected():
                self.conn = get_db_connection()
                self.cursor = self.conn.cursor()
            
            # Delete in correct order to handle foreign key constraints
            # 1. First delete team_tool_permissions
            self.cursor.execute("DELETE FROM team_tool_permissions WHERE team_id = %s", (self.team_id,))
            logger.info("Deleted team tool permissions")
            
            # 2. Delete team_agents
            self.cursor.execute("DELETE FROM team_agents WHERE team_id = %s", (self.team_id,))
            logger.info("Deleted team agents")
            
            # 3. Delete messages if any
            self.cursor.execute("DELETE FROM messages WHERE sender_id IN (%s, %s) OR receiver_id IN (%s, %s)", 
                              (self.sender_id, self.receiver_id, self.sender_id, self.receiver_id))
            logger.info("Deleted messages")
            
            # 4. Delete agent memory entries
            self.cursor.execute("DELETE FROM agent_memory WHERE agent_id IN (%s, %s)", 
                              (self.sender_id, self.receiver_id))
            logger.info("Deleted agent memory entries")
            
            # 5. Delete agent tools
            self.cursor.execute("DELETE FROM agent_tools WHERE agent_id IN (%s, %s)", 
                              (self.sender_id, self.receiver_id))
            logger.info("Deleted agent tools")
            
            # 6. Now safe to delete agents
            self.cursor.execute("DELETE FROM agents WHERE id IN (%s, %s)", 
                              (self.sender_id, self.receiver_id))
            logger.info("Deleted agents")
            
            # 7. Finally delete team
            self.cursor.execute("DELETE FROM teams WHERE id = %s", (self.team_id,))
            logger.info("Deleted team")
            
            self.conn.commit()
            logger.info("All test data cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error in test cleanup: {str(e)}")
            raise
        finally:
            safe_close_connection(self.conn, self.cursor)
            logger.info(f"Total cleanup time: {time.time() - start_time:.2f} seconds")
    
    def test_initialize_agent(self):
        """Test agent initialization"""
        start_time = time.time()
        logger.info("Starting agent initialization test...")
        
        response = requests.post(
            f"{self.base_url}/api/ml/agent/{self.sender_id}/initialize",
            json={
                "name": "Sender Agent",
                "memory_type": "SHORT_TERM_MEMORY",
                "foundation_model": "gpt-4",
                "use_prod": False
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        
        logger.info(f"Agent initialization test completed in {time.time() - start_time:.2f} seconds")
        
    def test_create_agent_memory(self):
        """Test creating agent memory"""
        start_time = time.time()
        logger.info("Starting agent memory creation test...")
        
        # First initialize the agent
        init_start = time.time()
        self.test_initialize_agent()
        logger.info(f"Agent initialization completed in {time.time() - init_start:.2f} seconds")
        
        # Test SHORT_TERM_MEMORY
        stm_start = time.time()
        response = requests.post(
            f"{self.base_url}/api/ml/agent-memory",
            json={
                "agent_id": self.sender_id,
                "memory_type": "SHORT_TERM_MEMORY",
                "start_prompt": "Test start prompt",
                "end_prompt": "Test end prompt"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        logger.info(f"SHORT_TERM_MEMORY creation completed in {time.time() - stm_start:.2f} seconds")
        
        # Test LONG_TERM_MEMORY
        ltm_start = time.time()
        response = requests.post(
            f"{self.base_url}/api/ml/agent-memory",
            json={
                "agent_id": self.sender_id,
                "memory_type": "LONG_TERM_MEMORY",
                "context": "Test context"
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        logger.info(f"LONG_TERM_MEMORY creation completed in {time.time() - ltm_start:.2f} seconds")
        
        logger.info(f"Total agent memory test completed in {time.time() - start_time:.2f} seconds")
        
    def test_send_message_to_agent(self):
        """Test sending message to agent"""
        start_time = time.time()
        logger.info("Starting message sending test...")
        
        # First initialize both agents
        init_start = time.time()
        self.test_initialize_agent()
        response = requests.post(
            f"{self.base_url}/api/ml/agent/{self.receiver_id}/initialize",
            json={
                "name": "Receiver Agent",
                "memory_type": "SHORT_TERM_MEMORY",
                "foundation_model": "gpt-4",
                "use_prod": False
            }
        )
        self.assertEqual(response.status_code, 200)
        logger.info(f"Agents initialization completed in {time.time() - init_start:.2f} seconds")
        
        # Then send a message
        send_start = time.time()
        response = requests.post(
            f"{self.base_url}/api/ml/agent/{self.sender_id}/send",
            json={
                "message": "How to build a python based databricks spark code?",
                "interaction_type": "direct",
                "team_id": self.team_id,
                "receiver_id": self.receiver_id
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        logger.info(f"Message sending completed in {time.time() - send_start:.2f} seconds")
        
        logger.info(f"Total message sending test completed in {time.time() - start_time:.2f} seconds")
        
    def test_end_to_end_workflow(self):
        """Test complete workflow of agent initialization and interaction"""
        start_time = time.time()
        logger.info("Starting end-to-end workflow test...")
        
        try:
            # 1. Initialize agent
            init_start = time.time()
            init_response = requests.post(
                f"{self.base_url}/api/ml/agent/{self.sender_id}/initialize",
                json={
                    "name": "Databricks Agent",
                    "memory_type": "SHORT_TERM_MEMORY",
                    "foundation_model": "gpt-4",
                    "use_prod": False
                }
            )
            self.assertEqual(init_response.status_code, 200)
            logger.info(f"Agent initialization completed in {time.time() - init_start:.2f} seconds")
            
            # 2. Create memories
            mem_start = time.time()
            short_term = requests.post(
                f"{self.base_url}/api/ml/agent-memory",
                json={
                    "agent_id": self.sender_id,
                    "memory_type": "SHORT_TERM_MEMORY",
                    "start_prompt": "You are a Databricks Agent and know Spark very well",
                    "end_prompt": "Have a Unit Test to verify your code"
                }
            )
            self.assertEqual(short_term.status_code, 200)
            
            long_term = requests.post(
                f"{self.base_url}/api/ml/agent-memory",
                json={
                    "agent_id": self.sender_id,
                    "memory_type": "LONG_TERM_MEMORY",
                    "context": "Apache Spark & Databricks best practices"
                }
            )
            self.assertEqual(long_term.status_code, 200)
            logger.info(f"Memory creation completed in {time.time() - mem_start:.2f} seconds")
            
            # 3. Add DBX tool to agent
            tool_start = time.time()
            tool_response = requests.post(
                f"{self.base_url}/api/ml/agent/{self.sender_id}/tools",
                json={
                    "tool_ids": [self.tool_id],
                    "team_id": self.team_id
                }
            )
            self.assertEqual(tool_response.status_code, 200)
            logger.info(f"Tool addition completed in {time.time() - tool_start:.2f} seconds")
            
            # 4. Execute command with all tools
            exec_start = time.time()
            execute_response = requests.post(
                f"{self.base_url}/api/ml/agent/{self.sender_id}/execute_all",
                json={
                    "command": "How to build a python based databricks spark code?",
                    "team_id": self.team_id
                },
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Enhanced error handling for execute_all
            if execute_response.status_code != 200:
                error_detail = None
                try:
                    error_detail = execute_response.json()
                except:
                    error_detail = execute_response.text
                
                logger.error(f"Execute_all failed with status {execute_response.status_code}")
                logger.error(f"Error details: {error_detail}")
                logger.error(f"Request URL: {execute_response.request.url}")
                logger.error(f"Request headers: {execute_response.request.headers}")
                logger.error(f"Request body: {execute_response.request.body}")
                
                # Check server status
                try:
                    health_check = requests.get(f"{self.base_url}/health", timeout=5)
                    logger.info(f"Server health check status: {health_check.status_code}")
                except Exception as e:
                    logger.error(f"Server health check failed: {str(e)}")
            
            self.assertEqual(execute_response.status_code, 200)
            logger.info(f"Command execution completed in {time.time() - exec_start:.2f} seconds")
            
            logger.info(f"Total end-to-end workflow test completed in {time.time() - start_time:.2f} seconds")
            
        except requests.exceptions.Timeout:
            logger.error("Request timed out - server might be overloaded or unresponsive")
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Connection error - server might be down")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during test: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during test: {str(e)}")
            raise

if __name__ == '__main__':
    unittest.main() 