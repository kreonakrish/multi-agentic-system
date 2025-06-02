const orchestrator = require('../services/orchestrator.service');
const logger = require('../utils/logger');

async function testOrchestratorService() {
    try {
        logger.info('Starting orchestrator service test');

        // Test data
        const messageData = {
            content: "Hello, can you help me with data analysis?",
            userId: "test-user-1",
            sessionId: "test-session-1",
            context: {
                team_id: "data-analysis-team",
                team_config: {
                    name: "Data Analysis Team",
                    description: "Team specialized in data analysis tasks",
                    members: [
                        {
                            agent_id: 10,
                            priority: 3,
                            accuracy_threshold: 0.9,
                            success_rate: 0.95,
                            role: "context_analyzer"
                        },
                        {
                            agent_id: 11,
                            priority: 2,
                            accuracy_threshold: 0.8,
                            success_rate: 0.9,
                            role: "response_generator"
                        }
                    ]
                },
                conversation_history: []
            }
        };

        logger.info('Test message data:', messageData);

        // Test processChatMessage
        logger.info('Testing processChatMessage...');
        const response = await orchestrator.processChatMessage(messageData);
        
        logger.info('Orchestrator response:', response);

        // Validate response structure
        if (!response || typeof response !== 'object') {
            throw new Error('Invalid response format: response should be an object');
        }

        if (!response.content) {
            throw new Error('Invalid response format: missing content');
        }

        if (!response.status) {
            throw new Error('Invalid response format: missing status');
        }

        if (!response.metadata) {
            throw new Error('Invalid response format: missing metadata');
        }

        logger.info('Test completed successfully');
        logger.info('Response validation passed');
        logger.info('Response content:', response.content);
        logger.info('Response metadata:', response.metadata);

        return {
            success: true,
            response
        };

    } catch (error) {
        logger.error('Test failed:', {
            error: error.message,
            stack: error.stack
        });

        return {
            success: false,
            error: error.message
        };
    }
}

// Run the test
testOrchestratorService()
    .then(result => {
        if (result.success) {
            logger.info('✅ All tests passed');
            logger.info('Sample response:', result.response);
        } else {
            logger.error('❌ Tests failed:', result.error);
        }
        process.exit(result.success ? 0 : 1);
    })
    .catch(error => {
        logger.error('❌ Test execution failed:', error);
        process.exit(1);
    }); 