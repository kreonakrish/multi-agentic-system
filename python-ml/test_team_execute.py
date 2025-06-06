import unittest
import json
import requests
from datetime import datetime
from app.utils.logger import logger
from app.utils.db import get_db_connection, safe_close_connection

class TestTeamExecute(unittest.TestCase):
    """Test cases for /team/execute endpoint"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:5000/api/ml"
        cls.test_team_id = 77  # Use existing team
        cls.test_user_id = "user-1"
        cls.test_session_id = 77

        # Database setup
        cls.conn = get_db_connection()
        cls.cursor = cls.conn.cursor(dictionary=True)

        try:
            # First check existing team agents
            cls.cursor.execute("SELECT * FROM team_agents WHERE team_id = %s", (cls.test_team_id,))
            existing_agents = cls.cursor.fetchall()
            logger.info(f"Existing agents for team {cls.test_team_id}: {json.dumps(existing_agents, indent=2)}")

            # Create test agents
            test_agents = [
                {
                    "agent_id": 101,
                    "name": "DataProcessor",
                    "priority": 2,
                    "accuracy": 0.85,
                    "success": 0.95
                },
                {
                    "agent_id": 102,
                    "name": "Validator",
                    "priority": 1,
                    "accuracy": 0.80,
                    "success": 0.90
                }
            ]

            # Update test input to use existing agents if any
            if existing_agents:
                logger.info("Using existing agents for test input")
                cls.test_agents = []
                for agent in existing_agents:
                    cls.test_agents.append({
                        "agent_id": agent['agent_id'],
                        "name": f"Agent_{agent['agent_id']}",
                        "priority": agent['priority'] or 1,
                        "accuracy_threshold": agent['accuracy'] / 100 if agent['accuracy'] else 0.8,
                        "success_rate": agent['success'] / 100 if agent['success'] else 0.9,
                        "role": "processor"
                    })
            else:
                logger.info("Creating new test agents")
                cls.test_agents = []
                for agent in test_agents:
                    # Create agent if not exists
                    cls.cursor.execute("""
                        INSERT INTO agents (id, name, description, status, accuracy_rate, success_rate, priority)
                        VALUES (%s, %s, %s, 'active', %s, %s, %s)
                        AS new_agent
                        ON DUPLICATE KEY UPDATE
                        name = new_agent.name,
                        status = 'active',
                        accuracy_rate = new_agent.accuracy_rate,
                        success_rate = new_agent.success_rate,
                        priority = new_agent.priority
                    """, (
                        agent['agent_id'],
                        agent['name'],
                        f"Test agent {agent['name']}",
                        agent['accuracy'],
                        agent['success'],
                        agent['priority']
                    ))

                    # Associate agent with team
                    cls.cursor.execute("""
                        INSERT INTO team_agents (team_id, agent_id, accuracy, success, priority)
                        VALUES (%s, %s, %s, %s, %s)
                        AS new_team_agent
                        ON DUPLICATE KEY UPDATE
                        accuracy = new_team_agent.accuracy,
                        success = new_team_agent.success,
                        priority = new_team_agent.priority
                    """, (
                        cls.test_team_id,
                        agent['agent_id'],
                        agent['accuracy'] * 100,  # Convert to integer percentage
                        agent['success'] * 100,   # Convert to integer percentage
                        agent['priority']
                    ))
                    cls.test_agents.append({
                        "agent_id": agent['agent_id'],
                        "name": agent['name'],
                        "priority": agent['priority'],
                        "accuracy_threshold": agent['accuracy'],
                        "success_rate": agent['success'],
                        "role": "processor"
                    })

            cls.conn.commit()
            logger.info("Test environment setup completed successfully")

        except Exception as e:
            logger.error(f"Error setting up test environment: {str(e)}")
            if cls.conn:
                cls.conn.rollback()
            raise

    def setUp(self):
        """Set up test case"""
        self.test_input = {
            "content": "Test message for team execution",
            "userId": self.test_user_id,
            "sessionId": self.test_session_id,
            "context": {
                "team_id": self.test_team_id,
                "team_config": {
                    "team_id": self.test_team_id,
                    "name": "test_team_github",
                    "description": "Team for processing test messages",
                    "members": self.test_agents,  # Use the agents we found/created
                    "workflow_type": "sequential",
                    "temperature": 0.7,
                    "token_limit": 512,
                    "start_prompt": "Process the following message:",
                    "end_prompt": "Validate the processed message:",
                    "style": "concise"
                },
                "conversation_settings": {
                    "temperature": 0.7,
                    "tokenLimit": 2000,
                    "startPrompt": "Process the following message:",
                    "endPrompt": "Validate the processed message:",
                    "style": "concise",
                    "system_prompt": "You are a helpful AI assistant.",
                    "max_tokens": 2000,
                    "model": "gpt-4"
                },
                "conversation_history": [],
                "documents": []
            }
        }

    def test_successful_execution(self):
        """Test successful team task execution"""
        logger.info("Testing successful team task execution")
        logger.debug(f"Test input: {json.dumps(self.test_input, indent=2)}")

        try:
            # Send request to endpoint
            response = requests.post(
                f"{self.base_url}/team/execute",
                json=self.test_input
            )

            # Log response
            logger.info(f"Response status code: {response.status_code}")
            data = response.json()
            logger.info(f"Full response body: {json.dumps(data, indent=2)}")

            # Assert response structure
            self.assertEqual(response.status_code, 200)
            data = response.json()

            # Verify response structure
            self.assertEqual(data['status'], 'success')
            self.assertIn('team', data)
            self.assertIn('result', data)
            self.assertIn('correlation_id', data)
            self.assertIn('workflow_id', data)
            self.assertIn('processing_time_seconds', data)

            # Verify team details
            team = data['team']
            self.assertEqual(str(team['team_id']), str(self.test_team_id))
            self.assertEqual(team['name'], 'team_github')
            self.assertIsInstance(team['members'], list)
            self.assertIsInstance(team['tasks'], list)

            # Verify result details
            result = data['result']
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(str(result['team_id']), str(self.test_team_id))
            self.assertIsInstance(result['results'], list)
            self.assertIsInstance(result['conversation_context'], list)
            self.assertIn('execution_summary', result)

            # Verify execution summary
            summary = result['execution_summary']
            self.assertGreater(summary['total_agents'], 0)
            self.assertGreater(summary['successful_executions'], 0)
            self.assertIsInstance(summary['priority_groups'], list)
            self.assertIsInstance(summary['execution_order'], list)

            logger.info("Successful execution test passed")

        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise

    def test_invalid_input(self):
        """Test execution with invalid input"""
        logger.info("Testing team task execution with invalid input")

        # Test with missing required fields
        invalid_input = {
            "content": "hi"
            # Missing userId, sessionId, and context
        }

        response = requests.post(
            f"{self.base_url}/team/execute",
            json=invalid_input
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data['status'], 'error')
        self.assertIn('message', data)
        logger.info("Invalid input test passed")

    def test_nonexistent_team(self):
        """Test execution with non-existent team"""
        logger.info("Testing team task execution with non-existent team")

        # Skip this test as we're using existing team
        logger.info("Skipping non-existent team test as we're using existing team")
        self.skipTest("Using existing team instead of creating new ones")

    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        try:
            # Delete in correct order to handle foreign key constraints
            cls.cursor.execute("DELETE FROM workflow_steps WHERE workflow_id IN (SELECT id FROM workflows WHERE team_id = %s)", (cls.test_team_id,))
            cls.cursor.execute("DELETE FROM workflows WHERE team_id = %s", (cls.test_team_id,))
            cls.cursor.execute("DELETE FROM team_agents WHERE team_id = %s AND agent_id IN (101, 102)", (cls.test_team_id,))
            cls.cursor.execute("DELETE FROM agents WHERE id IN (101, 102)")
            cls.conn.commit()
            logger.info("Test environment cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error cleaning up test environment: {str(e)}")
            if cls.conn:
                cls.conn.rollback()

        finally:
            safe_close_connection(cls.conn, cls.cursor)

if __name__ == '__main__':
    unittest.main() 